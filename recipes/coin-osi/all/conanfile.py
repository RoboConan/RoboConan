import os
import shutil

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag

required_conan_version = ">=2.1"


class CoinOsiConan(ConanFile):
    name = "coin-osi"
    description = "COIN-OR Linear Programming Solver"
    topics = ("clp", "simplex", "solver", "linear", "programming")
    homepage = "https://github.com/coin-or/Osi"
    license = "EPL-2.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_glpk": [True, False],
        "with_soplex": [True, False],
        "with_cplex": [True, False],
        "with_mosek": [True, False],
        "with_xpress": [True, False],
        "with_gurobi": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_glpk": False,
        "with_soplex": False,
        "with_cplex": False,
        "with_mosek": False,
        "with_xpress": False,
        "with_gurobi": False,
    }
    implements = ["auto_shared_fpic"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.shared
            self.package_type = "static-library"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("coin-utils/[^2.11.11]")
        if self.options.with_glpk:
            self.requires("glpk/[<=4.48]")
        if self.options.with_soplex:
            self.requires("soplex/[<4]")
        if self.options.with_cplex:
            # Cbc expects cplex.h to be available
            self.requires("cplex/[*]", transitive_headers=True)
        if self.options.with_mosek:
            self.requires("mosek/[<10]")
        if self.options.with_xpress:
            self.requires("xpress/[*]")
        if self.options.with_gurobi:
            self.requires("gurobi/[*]")

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
        replace_in_file(self, "Osi/configure.ac", "coinsoplex < 1.7", "coinsoplex")

    def generate(self):
        yes_no = lambda v: "yes" if v else "no"
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--with-glpk={yes_no(self.options.with_glpk)}",
            f"--with-soplex={yes_no(self.options.with_soplex)}",
            f"--enable-cplex-libcheck={yes_no(self.options.with_cplex)}",
            f"--enable-mosek-libcheck={yes_no(self.options.with_mosek)}",
            f"--enable-xpress-libcheck={yes_no(self.options.with_xpress)}",
            f"--enable-gurobi-libcheck={yes_no(self.options.with_gurobi)}",
            # These are only used for sample datasets
            "--without-netlib",
            "--without-sample",
            "F77=unavailable",
        ])

        def _libflags(name):
            dep_info = self.dependencies[name].cpp_info.aggregated_components()
            flags = [f"-L{lib}" for lib in dep_info.libdirs]
            flags += [f"-l{lib}" for lib in dep_info.libs]
            flags += [f"-l{lib}" for lib in dep_info.system_libs]
            return " ".join(flags)

        if self.options.with_cplex:
            tc.configure_args.append(f"--with-cplex-incdir={self.dependencies['cplex'].package_folder}/include/ilcplex")
            tc.configure_args.append(f"--with-cplex-lib={_libflags('cplex')}")
        if self.options.with_mosek:
            tc.configure_args.append(f"--with-mosek-incdir={self.dependencies['mosek'].package_folder}/include")
            tc.configure_args.append(f"--with-mosek-lib={_libflags('mosek')}")
        if self.options.with_xpress:
            tc.configure_args.append(f"--with-xpress-incdir={self.dependencies['xpress'].package_folder}/include")
            tc.configure_args.append(f"--with-xpress-lib={_libflags('xpress')}")
        if self.options.with_gurobi:
            tc.configure_args.append(f"--with-gurobi-incdir={self.dependencies['gurobi'].package_folder}/include")
            tc.configure_args.append(f"--with-gurobi-lib={_libflags('gurobi')}")

        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
            tc.configure_args.append(f"--enable-msvc={msvc_runtime_flag(self)}")
        env = tc.environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        if is_msvc(self):
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", "lib -nologo")
        tc.generate(env)

        deps = PkgConfigDeps(self)
        deps.set_property("glpk", "pkg_config_aliases", ["coinglpk"])
        deps.set_property("soplex", "pkg_config_aliases", ["coinsoplex"])
        deps.generate()

    def build(self):
        buildtools = self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0]
        copy(self, "*", buildtools, os.path.join(self.source_folder, "Osi", "BuildTools"))
        replace_in_file(self, os.path.join(self.source_folder, "Osi", "configure.ac"),
                        "AC_CANONICAL_BUILD",
                        "AC_CANONICAL_BUILD\nAC_CANONICAL_HOST")
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "Osi"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="Osi")
        autotools.configure(build_script_folder="Osi")
        if is_msvc(self):
            replace_in_file(self, os.path.join(self.build_folder, "libtool"),
                            r"\$AR \$AR_FLAGS \$oldlib",
                            r"\$AR -OUT:\$oldlib")
            replace_in_file(self, os.path.join(self.build_folder, "Makefile"),
                            " install-data-hook", "")
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.components["libosi"].set_property("pkg_config_name", "osi")
        self.cpp_info.components["libosi"].libs = ["Osi"]
        self.cpp_info.components["libosi"].includedirs = [os.path.join("include", "coin")]
        self.cpp_info.components["libosi"].requires = ["coin-utils::coin-utils"]

        self.cpp_info.components["osi-unittests"].set_property("pkg_config_name", "osi-unittests")
        self.cpp_info.components["osi-unittests"].libs = ["OsiCommonTests"]
        self.cpp_info.components["osi-unittests"].requires = ["libosi"]

        if self.options.with_glpk:
            self.cpp_info.components["osi-glpk"].set_property("pkg_config_name", "osi-glpk")
            self.cpp_info.components["osi-glpk"].libs = ["OsiGlpk"]
            self.cpp_info.components["osi-glpk"].requires = ["libosi", "glpk::glpk"]

        if self.options.with_soplex:
            self.cpp_info.components["osi-soplex"].set_property("pkg_config_name", "osi-soplex")
            self.cpp_info.components["osi-soplex"].libs = ["OsiSpx"]
            self.cpp_info.components["osi-soplex"].requires = ["libosi", "soplex::soplex"]

        if self.options.with_cplex:
            self.cpp_info.components["osi-cplex"].set_property("pkg_config_name", "osi-cplex")
            self.cpp_info.components["osi-cplex"].libs = ["OsiCpx"]
            self.cpp_info.components["osi-cplex"].requires = ["libosi", "cplex::cplex_"]

        if self.options.with_mosek:
            self.cpp_info.components["osi-mosek"].set_property("pkg_config_name", "osi-mosek")
            self.cpp_info.components["osi-mosek"].libs = ["OsiMsk"]
            self.cpp_info.components["osi-mosek"].requires = ["libosi", "mosek::mosek"]

        if self.options.with_xpress:
            self.cpp_info.components["osi-xpress"].set_property("pkg_config_name", "osi-xpress")
            self.cpp_info.components["osi-xpress"].libs = ["OsiXpr"]
            self.cpp_info.components["osi-xpress"].requires = ["libosi", "xpress::xpress"]

        if self.options.with_gurobi:
            self.cpp_info.components["osi-gurobi"].set_property("pkg_config_name", "osi-gurobi")
            self.cpp_info.components["osi-gurobi"].libs = ["OsiGrb"]
            self.cpp_info.components["osi-gurobi"].requires = ["libosi", "gurobi::gurobi"]
