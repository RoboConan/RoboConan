import os
import shutil

from conan import ConanFile
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class CoinDipConan(ConanFile):
    name = "coin-dip"
    description = "DIP is a decomposition-based solver framework for mixed integer linear programs."
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Dip"
    topics = ("optimization", "mixed-integer-linear-programming", "coin-or")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_asl": [True, False],
        "with_cbc": [True, False],
        "with_clp": [True, False],
        "with_symphony": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_asl": False,
        "with_cbc": False,
        "with_clp": True,
        "with_symphony": False,
        "with_openmp": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.shared
            self.package_type = "static-library"

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("coin-utils/[^2.11.11]", transitive_headers=True, transitive_libs=True)
        self.requires("coin-osi/[>=0.108.10 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("coin-alps/[^1.5]", transitive_headers=True, transitive_libs=True)
        self.requires("coin-cgl/[>=0.60.8 <1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_asl:
            self.requires("ampl-asl/[^1]")
        if self.options.with_clp:
            self.requires("coin-clp/[^1.17.9]", transitive_headers=True, transitive_libs=True)
        if self.options.with_cbc:
            self.requires("coin-cbc/[^2.10]", transitive_headers=True, transitive_libs=True)
        if self.options.with_symphony:
            self.requires("coin-symphony/[^5.7.2]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openmp:
            self.requires("openmp/system")

    def build_requirements(self):
        self.tool_requires("coin-buildtools/[*]")
        self.tool_requires("gnu-config/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "Dip/src/Makefile.am",
                        "cp dip.exe $(bindir)/dip.exe",
                        "cp dip.exe $(DESTDIR)$(bindir)/dip.exe")

    def generate(self):
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        osi = self.dependencies["coin-osi"]
        tc.configure_args += [
            f"--with-asl={yes_no(self.options.with_asl)}",
            f"--with-clp={yes_no(self.options.with_clp)}",
            f"--with-cbc={yes_no(self.options.with_cbc)}",
            f"--with-symphony={yes_no(self.options.with_symphony)}",
            f"--with-cpx={yes_no(osi.options.with_cplex)}",
            f"--with-grb={yes_no(osi.options.with_gurobi)}",
            f"--with-xpr={yes_no(osi.options.with_xpress)}",
            f"--enable-openmp={yes_no(self.options.with_openmp)}",
            "F77=unavailable",
            f"PYTHON=echo",
        ]

        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")

        env = tc.environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
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

        deps = PkgConfigDeps(self)
        deps.set_property("ampl-asl::asl", "pkg_config_aliases", ["coinasl"])
        deps.generate()

    def build(self):
        buildtools = self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0]
        copy(self, "*", buildtools, os.path.join(self.source_folder, "Dip", "BuildTools"))
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "Dip"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="Dip")
        autotools.configure(build_script_folder="Dip")
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

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "dip")
        self.cpp_info.libs = ["Decomp"]
        self.cpp_info.includedirs.append("include/coin")
        self.cpp_info.requires = [
            "coin-utils::coin-utils",
            "coin-osi::libosi",
            "coin-alps::coin-alps",
            "coin-cgl::coin-cgl",
        ]
        if self.options.with_asl:
            self.cpp_info.requires.append("ampl-asl::asl")
        if self.options.with_clp:
            self.cpp_info.requires.append("coin-clp::osi-clp")
        if self.options.with_cbc:
            self.cpp_info.requires.append("coin-cbc::libcbc")
            self.cpp_info.requires.append("coin-cbc::osi-cbc")
        if self.options.with_symphony:
            self.cpp_info.requires.append("coin-symphony::osi-sym")
        if self.dependencies["coin-osi"].options.with_cplex:
            self.cpp_info.requires.append("coin-osi::osi-cplex")
        if self.dependencies["coin-osi"].options.with_gurobi:
            self.cpp_info.requires.append("coin-osi::osi-gurobi")
        if self.dependencies["coin-osi"].options.with_xpress:
            self.cpp_info.requires.append("coin-osi::osi-xpress")
        if self.options.with_openmp:
            self.cpp_info.requires.append("openmp::openmp")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]
