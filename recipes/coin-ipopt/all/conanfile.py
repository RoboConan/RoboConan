import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import stdcpp_library
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, PkgConfig
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class CoinClpConan(ConanFile):
    name = "coin-ipopt"
    description = "COIN-OR Interior Point Optimizer IPOPT"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Ipopt"
    topics = ("optimization", "interior-point", "nonlinear-optimization", "nonconvex")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_sipopt": [True, False],
        "precision": ["single", "double"],
        "enable_inexact_solver": [True, False],
        "with_asl": [True, False],
        "with_mumps": [True, False],
        "with_hsl": [True, False],
        "with_spral": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_sipopt": True,
        "precision": "double",
        "enable_inexact_solver": False,
        "with_asl": False,
        "with_mumps": False,
        "with_hsl": False,
        "with_spral": True,
    }
    implements = ["auto_shared_fpic"]

    def configure(self):
        # Shared builds on Windows are not supported yet
        if self.settings.os == "Windows":
            self.options.shared.value = False
            self.package_type = "static-library"
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        if self.options.with_asl:
            self.requires("ampl-asl/[^1]")
        if self.options.with_mumps:
            self.requires("coin-mumps/[^3.0.5]")
        if self.options.with_hsl:
            self.requires("coin-hsl/[*]")
        if self.options.with_spral:
            self.requires("spral/[*]")
        # TODO: optionally use MKL instead of OpenBLAS for pardisomkl solver support

    @property
    def _int_size(self):
        return 32 if self.dependencies["blas"].options.interface == "lp64" else 64

    def validate(self):
        if self.options.with_asl and self.options.precision != "double":
            raise ConanInvalidConfiguration("ASL solver requires double precision")
        if self.options.with_spral and (self.options.precision != "double" or self._int_size != 32):
            raise ConanInvalidConfiguration("SPRAL solver requires double precision and 32-bit integers")

    def build_requirements(self):
        self.tool_requires("coin-buildtools/[*]")
        self.tool_requires("gnu-config/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if is_msvc(self):
            self.tool_requires("automake/[^1.18.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _flags_from_pc(self, name):
        pc = PkgConfig(self, name, self.generators_folder)
        cflags = list(pc.cflags)
        cflags += [f"-I{inc}" for inc in pc.includedirs]
        ldflags = list(pc.linkflags)
        ldflags += [f"-L{libdir}" for libdir in pc.libdirs]
        ldflags += [f"-l{lib}" for lib in pc.libs]
        return " ".join(cflags), " ".join(ldflags)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.set_property("ampl-asl::asl2-mt", "pkg_config_aliases", ["coinasl"])
        deps.generate()

        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        int_size = 32 if self.dependencies["blas"].options.interface == "lp64" else 64
        tc.configure_args += [
            "--with-lapack=yes",
            f"--with-intsize={int_size}",
            f"--with-precision={self.options.precision}",
            f"--enable-inexact-solver={yes_no(self.options.enable_inexact_solver)}",
            f"--enable-sipopt={yes_no(self.options.build_sipopt)}",
            f"--with-asl={yes_no(self.options.with_asl)}",
            f"--with-mumps={yes_no(self.options.with_mumps)}",
            f"--with-hsl={yes_no(self.options.with_hsl)}",
            f"--with-spral={yes_no(self.options.with_spral)}",
            "--with-dot=no",
            "--disable-f77",
            "--disable-java",
        ]

        if self.options.with_spral:
            cflags, ldflags = self._flags_from_pc("spral")
            tc.configure_args.append(f"--with-spral-cflags={cflags}")
            tc.configure_args.append(f"--with-spral-lflags={ldflags}")

        cflags, ldflags = self._flags_from_pc("lapack")
        tc.configure_args.append(f"--with-lapack-cflags={cflags}")
        tc.configure_args.append(f"--with-lapack-lflags={ldflags}")

        env = tc.environment()
        if is_msvc(self):
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", f"{compile_wrapper} link -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")
        tc.generate(env)

    def build(self):
        buildtools = self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0]
        copy(self, "*", buildtools, os.path.join(self.source_folder, "BuildTools"))
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.components["ipopt"].set_property("pkg_config_name", "ipopt")
        self.cpp_info.components["ipopt"].libs = ["ipopt"]
        self.cpp_info.components["ipopt"].includedirs.append("include/coin-or")
        self.cpp_info.components["ipopt"].requires = ["lapack::lapack"]
        if self.options.with_mumps:
            self.cpp_info.components["ipopt"].requires.append("coin-mumps::coin-mumps")
        if self.options.with_hsl:
            self.cpp_info.components["ipopt"].requires.append("coin-hsl::coin-hsl")
        if self.options.with_spral:
            self.cpp_info.components["ipopt"].requires.append("spral::spral")
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["ipopt"].system_libs = ["m", "dl"]
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.components["ipopt"].system_libs.append(libcxx)

        if self.options.build_sipopt:
            self.cpp_info.components["sipopt"].set_property("pkg_config_name", "sipopt")
            self.cpp_info.components["sipopt"].libs = ["sipopt"]
            self.cpp_info.components["sipopt"].includedirs.append("include/coin-or")
            self.cpp_info.components["sipopt"].requires = ["ipopt"]

        if self.options.with_asl:
            self.cpp_info.components["ipoptamplinterface"].set_property("pkg_config_name", "ipoptamplinterface")
            self.cpp_info.components["ipoptamplinterface"].libs = ["ipoptamplinterface"]
            self.cpp_info.components["ipoptamplinterface"].includedirs.append("include/coin-or")
            self.cpp_info.components["ipoptamplinterface"].requires = ["ipopt", "ampl-asl::asl2-mt"]
