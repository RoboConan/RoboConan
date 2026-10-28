import os
import shutil

from conan import ConanFile
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, PkgConfig
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class BonminConan(ConanFile):
    name = "coin-bonmin"
    description = "Bonmin: Basic Open-source Nonlinear Mixed Integer programming"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Bonmin"
    topics = ("optimization", "mixed-integer-nonlinear-programming", "coin-or")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "with_asl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "with_asl": False,
    }
    implements = ["auto_shared_fpic"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.shared
            del self.options.fPIC
            self.package_type = "static-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        self.options["coin-ipopt"].with_asl = self.options.with_asl

    def requirements(self):
        self.requires("coin-cbc/[^2.10.12]")
        self.requires("coin-clp/[^1.17.9]")
        self.requires("coin-osi/[>=0.108.10 <1]")
        self.requires("coin-ipopt/[^3.14.19]", transitive_headers=True, transitive_libs=True)
        if self.options.with_asl:
            self.requires("ampl-asl/[^1]")
        # Optionally also supports FilterSQP commercial software

    def build_requirements(self):
        self.tool_requires("coin-buildtools/[*]")
        self.tool_requires("gnu-config/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if is_msvc(self):
            self.tool_requires("automake/[^1.18.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "Bonmin/src/Apps/Makefile.am",
                        "cp bonmin.exe $(bindir)/bonmin.exe",
                        "cp bonmin.exe $(DESTDIR)$(bindir)/bonmin.exe")

    def _flags_from_pc(self, name):
        pc = PkgConfig(self, name, self.generators_folder)
        cflags = list(pc.cflags)
        cflags += [f"-I{unix_path(self, inc)}" for inc in pc.includedirs]
        ldflags = list(pc.linkflags)
        ldflags += [f"-L{unix_path(self, libdir)}" for libdir in pc.libdirs]
        ldflags += [f"-l{lib}" for lib in pc.libs]
        return " ".join(cflags), " ".join(ldflags)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.set_property("ampl-asl::asl", "pkg_config_aliases", ["coinasl"])
        deps.generate()

        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        osi = self.dependencies["coin-osi"]
        tc.configure_args += [
            f"--with-asl={yes_no(self.options.with_asl)}",
            f"--with-osicpx={yes_no(osi.options.with_cplex)}",
            "--with-filtersqp=no",
            "F77=unavailable",
        ]

        if osi.options.with_cplex:
            _, ldflags = self._flags_from_pc("cplex")
            tc.configure_args.append(f"--with-cplex-incdir={unix_path(self, self.dependencies['cplex'].cpp_info.includedir)}/ilcplex")
            tc.configure_args.append(f"--with-cplex-lib={ldflags}")

        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")

        env = tc.environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        if str(self.settings.compiler) in ["gcc", "clang", "apple-clang"]:
            # The old configure script probes GNU C before initializing the object suffix.
            env.define("ac_cv_c_compiler_gnu", "yes")
        if is_msvc(self):
            automake = self.dependencies.build["automake"]
            compile_wrapper = unix_path(self, automake.conf_info.get("user.automake:compile-wrapper"))
            ar_wrapper = unix_path(self, automake.conf_info.get("user.automake:lib-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("NM", "dumpbin -symbols")
            env.vars(self).save_script("conanbuild_msvc")
        tc.generate(env)

    def build(self):
        buildtools = self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0]
        copy(self, "*", buildtools, os.path.join(self.source_folder, "Bonmin", "BuildTools"))
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "Bonmin"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="Bonmin")
        autotools.configure(build_script_folder="Bonmin")
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Installation script expects include/coin to already exist
        mkdir(self, os.path.join(self.package_folder, "include", "coin"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        if not self.options.tools:
            suffix = ".exe" if self.settings.os == "Windows" else ""
            rm(self, "bonmin" + suffix, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.components["libbonmin"].set_property("pkg_config_name", "bonmin")
        self.cpp_info.components["libbonmin"].libs = ["bonmin"]
        self.cpp_info.components["libbonmin"].includedirs.append("include/coin")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libbonmin"].system_libs = ["m", "pthread", "rt", "dl"]
        self.cpp_info.components["libbonmin"].requires = [
            "coin-cbc::libcbc",
            "coin-clp::osi-clp",
            "coin-osi::libosi",
            "coin-ipopt::ipopt",
        ]
        if self.dependencies["coin-osi"].options.with_cplex:
            self.cpp_info.components["libbonmin"].requires.append("coin-osi::osi-cplex")

        if self.options.with_asl:
            self.cpp_info.components["bonminamplinterface"].set_property("pkg_config_name", "bonminamplinterface")
            self.cpp_info.components["bonminamplinterface"].libs = ["bonminampl"]
            self.cpp_info.components["bonminamplinterface"].includedirs.append("include/coin")
            self.cpp_info.components["bonminamplinterface"].requires = [
                "libbonmin",
                "coin-ipopt::ipoptamplinterface",
                "ampl-asl::asl",
            ]
