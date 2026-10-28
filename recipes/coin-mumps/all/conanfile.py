import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, PkgConfig
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path

required_conan_version = ">=2.13"


class CoinMumpsConan(ConanFile):
    name = "coin-mumps"
    description = "MUltifrontal Massively Parallel sparse direct Solver (MUMPS)"
    license = "CECILL-C AND EPL-1.0"
    homepage = "https://github.com/coin-or-tools/ThirdParty-Mumps"
    topics = ("solver", "sparse", "direct", "parallel", "linear-algebra")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    options = {
        "precision": ["single", "double", "all"],
        "with_openmp": [True, False],
        "with_pthread": [True, False],
    }
    default_options = {
        "precision": "double",
        "with_openmp": True,
        "with_pthread": True,
    }
    languages = ["C"]

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        self.fortran.validate_settings()

    def requirements(self):
        self.requires("lapack/latest")
        self.requires("metis/[^5.2.1]")
        self.fortran.requires_runtime()
        if self.options.with_openmp:
            self.requires("openmp/system")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def validate_build(self):
        self.fortran.validate_build()

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["build_scripts"], strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["source"], destination="MUMPS", strip_root=True)
        # Mirror get.Mumps, but use the source archive already downloaded by Conan.
        for patch_file in ("mumps_mpi.patch", "mumps_call.patch", "mumps_stdalign.patch"):
            patch(self, patch_file=os.path.join(self.source_folder, patch_file))
        os.rename("MUMPS/libseq/mpi.h", "MUMPS/libseq/mumps_mpi.h")

    def _flags_from_pc(self, name):
        pc = PkgConfig(self, name, self.generators_folder)
        cflags = list(pc.cflags)
        cflags += [f"-D{define}" for define in pc.defines]
        cflags += [f"-I{unix_path(self, inc)}" for inc in pc.includedirs]
        ldflags = list(pc.linkflags)
        ldflags += [f"-L{unix_path(self, libdir)}" for libdir in pc.libdirs]
        ldflags += [f"-l{lib}" for lib in pc.libs]
        return " ".join(cflags), " ".join(ldflags)

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        deps = PkgConfigDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        int_size = 32 if self.dependencies["blas"].options.interface == "lp64" else 64
        tc.configure_args.extend([
            "--with-lapack=yes",
            "--with-metis=yes",
            f"--enable-pthread-mumps={yes_no(self.options.with_pthread)}",
            f"--enable-openmp={yes_no(self.options.with_openmp)}",
            f"--with-precision={self.options.precision}",
            f"--with-intsize={int_size}",
            f"FC={self.fortran.executable}",
        ])
        _, ldflags = self._flags_from_pc("lapack")
        tc.configure_args.append(f"--with-lapack-lflags={ldflags}")
        cflags, ldflags = self._flags_from_pc("metis")
        tc.configure_args.append(f"--with-metis-cflags={cflags}")
        tc.configure_args.append(f"--with-metis-lflags={ldflags}")
        env = tc.environment()
        if self.settings.os == "Windows" and self.fortran.compiler == "ifx":
            # MUMPS' Fortran sources use configure-provided preprocessor definitions.
            env.append("FCFLAGS", "/fpp")
        tc.generate(env)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        mkdir(self, os.path.join(self.package_folder, "licenses"))
        shutil.copy(os.path.join(self.source_folder, "LICENSE"),
                    os.path.join(self.package_folder, "licenses", "LICENSE-coin-mumps"))
        shutil.copy(os.path.join(self.source_folder, "MUMPS", "LICENSE"),
                    os.path.join(self.package_folder, "licenses", "LICENSE-MUMPS"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "coinmumps")
        self.cpp_info.libs = ["coinmumps"]
        self.cpp_info.includedirs.append("include/coin-or")
        self.cpp_info.includedirs.append("include/coin-or/mumps")
        if not self.options.get_safe("shared", True):
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs.extend(["m"])
                if self.options.with_pthread:
                    self.cpp_info.system_libs.extend(["pthread"])

        self.cpp_info.requires = [
            "lapack::lapack",
            "metis::metis",
        ]
        if self.options.with_openmp:
            self.cpp_info.requires.append("openmp::openmp")
        self.fortran.add_runtime_to_cpp_info(self.cpp_info)
