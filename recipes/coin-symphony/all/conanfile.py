import os
import shutil

from conan import ConanFile
from conan.tools.build import stdcpp_library
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, unix_path

required_conan_version = ">=2.1"


class SymphonyConan(ConanFile):
    name = "coin-symphony"
    description = "SYMPHONY: A callable library for solving mixed-integer linear programs"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/SYMPHONY"
    topics = ("optimization", "linear-programming", "coin-or", "integer-programming", "mixed-integer-programming")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "application_library": [True, False],
        "default_lp_solver": ["clp", "cplex", "glpk", "soplex", "xpress"],
        "tools": [True, False],
        "with_clp": [True, False],
        "with_dylp": [True, False],
        "with_vol": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "application_library": False,
        "default_lp_solver": "clp",
        "tools": False,
        "with_clp": True,
        "with_dylp": False,
        "with_vol": False,
        "with_openmp": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("coin-utils/[^2.11.11]")
        self.requires("coin-osi/[>=0.108.10 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("coin-cgl/[>=0.60.8 <1]")

        if self.options.with_clp:
            self.requires("coin-clp/[^1.17.9]")
        if self.options.with_dylp:
            self.requires("coin-dylp/[^1.10.4]")
        if self.options.with_vol:
            self.requires("coin-vol/[^1.5.4]")

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

    def generate(self):
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        osi = self.dependencies["coin-osi"]
        tc.configure_args += [
            f"--with-lp-solver={self.options.default_lp_solver}",
            "--with-cgl=yes",  # can't be disabled
            f"--with-clp={yes_no(self.options.with_clp)}",
            f"--with-osiclp={yes_no(self.options.with_clp)}",
            f"--with-dylp={yes_no(self.options.with_dylp)}",
            f"--with-osidylp={yes_no(self.options.with_dylp)}",
            f"--with-vol={yes_no(self.options.with_vol)}",
            f"--with-osivol={yes_no(self.options.with_vol)}",
            f"--with-osicplex={yes_no(osi.options.with_cplex)}",
            f"--with-osiglpk={yes_no(osi.options.with_glpk)}",
            f"--with-osigurobi={yes_no(osi.options.with_gurobi)}",
            f"--with-osimosek={yes_no(osi.options.with_mosek)}",
            f"--with-osisoplex={yes_no(osi.options.with_soplex)}",
            f"--with-osixpress={yes_no(osi.options.with_xpress)}",
            f"--with-gmpl={yes_no(osi.options.with_glpk)}",
            f"--enable-openmp={yes_no(self.options.with_openmp)}",
            f"--with-application={yes_no(self.options.application_library)}",
            "--with-cg",  # cut generator module
            "--with-cp",  # cut pool module
            "--with-lp",  # LP solver module
            "--with-tm",  # tree manager module
            # Only used for sample data
            "--without-netlib",
            "--without-sample",
            "--without-miplib3",
            "F77=unavailable",
        ]
        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
            tc.configure_args.append(f"--enable-msvc={msvc_runtime_flag(self)}")
        tc.generate()

        env = tc.environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        if is_msvc(self):
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("NM", "dumpbin -symbols")
            env.vars(self).save_script("conanbuild_msvc")
        tc.generate(env)

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        buildtools = self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0]
        copy(self, "*", buildtools, os.path.join(self.source_folder, "SYMPHONY", "BuildTools"))
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "SYMPHONY"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="SYMPHONY")
        autotools.configure(build_script_folder="SYMPHONY")
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Installation script expects include/coin to already exist
        mkdir(self, os.path.join(self.package_folder, "include", "coin"))
        save(self, os.path.join(self.build_folder, "src", ".libs", "libSym.lai"), "")
        save(self, os.path.join(self.build_folder, "src", ".libs", "libSymAppl.lai"), "")
        save(self, os.path.join(self.build_folder, "src", ".libs", "libSymApplStubs.lai"), "")
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        if not self.options.tools:
            rm(self, "symphony*", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.components["libsym"].set_property("pkg_config_name", "symphony")
        self.cpp_info.components["libsym"].libs = ["Sym"]
        self.cpp_info.components["libsym"].includedirs.append("include/coin")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libsym"].system_libs = ["m", "pthread", "rt", "dl"]
        if stdcpp_library(self):
            self.cpp_info.components["libsym"].system_libs.append(stdcpp_library(self))
        requires = [
            "coin-utils::coin-utils",
            "coin-osi::coin-osi",
            "coin-cgl::coin-cgl",
        ]
        if self.options.with_clp:
            requires.append("coin-clp::coin-clp")
        if self.options.with_dylp:
            requires.append("coin-dylp::coin-dylp")
        if self.options.with_vol:
            requires.append("coin-vol::coin-vol")
        if self.options.with_openmp:
            requires.append("openmp::openmp")
        self.cpp_info.components["libsym"].requires = requires

        self.cpp_info.components["osi-sym"].set_property("pkg_config_name", "osi-sym")
        self.cpp_info.components["osi-sym"].libs = ["OsiSym"]
        self.cpp_info.components["osi-sym"].requires = ["libsym", "coin-osi::coin-osi"]

        if self.options.application_library:
            self.cpp_info.components["symphony-app"].set_property("pkg_config_name", "symphony-app")
            self.cpp_info.components["symphony-app"].libs = ["SymAppl"]
            self.cpp_info.components["symphony-app"].includedirs.append("include/coin")
            self.cpp_info.components["symphony-app"].requires = requires
