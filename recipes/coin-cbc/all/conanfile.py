import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, unix_path

required_conan_version = ">=2.1"


class CoinCbcConan(ConanFile):
    name = "coin-cbc"
    description = "COIN-OR Branch-and-Cut solver"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Cbc"
    topics = ("cbc", "branch-and-cut", "solver", "linear", "programming")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "parallel": [True, False],
        "with_asl": [True, False],
        "with_nauty": [True, False],
        "with_dylp": [True, False],
        "with_vol": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "parallel": True,
        "with_asl": False,
        "with_nauty": True,
        "with_dylp": False,
        "with_vol": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.shared
            self.package_type = "static-library"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("coin-utils/[^2.11.11]", transitive_headers=True, transitive_libs=True)
        self.requires("coin-osi/[>=0.108.10 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("coin-cgl/[>=0.60.8 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("coin-clp/[^1.17.9]", transitive_headers=True, transitive_libs=True)
        if self.options.with_asl:
            self.requires("ampl-asl/[^1]")
        if self.options.with_nauty:
            self.requires("nauty/[^2.9.1]")
        if self.options.with_dylp:
            self.requires("coin-dylp/[^1.10.4]")
        if self.options.with_vol:
            self.requires("coin-vol/[^1.5.4]")
        if is_msvc(self) and self.options.parallel:
            self.requires("pthreads4w/[^3.0.0]")

    def validate(self):
        if self.dependencies["coin-osi"].options.with_glpk and not self.dependencies["coin-clp"].options.with_glpk:
            # Cbc tries to use some GLPK features from Clp if GLPK is enabled in Osi, even if it's not correct.
            raise ConanInvalidConfiguration("-o coin-clp/*:with_glpk must be True if -o coin-osi/*:with_glpk=True")

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
        replace_in_file(self, "Cbc/src/CbcSymmetry.hpp", '#include "nauty/', '#include "')

    def generate(self):
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        osi = self.dependencies["coin-osi"]
        tc.configure_args += [
            f"--enable-cbc-parallel={yes_no(self.options.parallel)}",
            f"--with-asl={yes_no(self.options.with_asl)}",
            f"--enable-nauty-libcheck={yes_no(self.options.with_nauty)}",
            f"--with-osidylp={yes_no(self.options.with_dylp)}",
            f"--with-osivol={yes_no(self.options.with_vol)}",
            f"--with-osicplex={yes_no(osi.options.with_cplex)}",
            f"--with-osiglpk={yes_no(osi.options.with_glpk)}",
            f"--with-osigurobi={yes_no(osi.options.with_gurobi)}",
            f"--with-osimosek={yes_no(osi.options.with_mosek)}",
            f"--with-osisoplex={yes_no(osi.options.with_soplex)}",
            f"--with-osixpress={yes_no(osi.options.with_xpress)}",
            "--with-mumps=no",  # not really used
            "--with-osihighs=no",  # still under development
            # Only used for sample data
            "--without-netlib",
            "--without-sample",
            "--without-miplib3",
            "F77=unavailable",
        ]
        if self.options.with_nauty:
            nauty_info = self.dependencies["nauty"].cpp_info
            tc.configure_args.append(f"--with-nauty-lib=-l{nauty_info.libs[0]} -L{unix_path(self, nauty_info.libdir)}")
            tc.configure_args.append(f"--with-nauty-incdir={unix_path(self, nauty_info.includedir)}")
        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
            tc.configure_args.append(f"--enable-msvc={msvc_runtime_flag(self)}")
            if self.options.parallel:
                pthreads4w_info = self.dependencies["pthreads4w"].cpp_info
                pthreads_path = os.path.join(pthreads4w_info.libdir, pthreads4w_info.libs[0] + ".lib")
                tc.configure_args.append(f"--with-pthreadsw32-lib={unix_path(self, pthreads_path)}")
                tc.configure_args.append(f"--with-pthreadsw32-incdir={unix_path(self, pthreads4w_info.includedir)}")
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
        deps.set_property("ampl-asl", "pkg_config_aliases", ["coinasl"])
        deps.generate()

    def build(self):
        buildtools = self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0]
        copy(self, "*", buildtools, os.path.join(self.source_folder, "Cbc", "BuildTools"))
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "Cbc"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="Cbc")
        # Fix a failure on Windows. The am data is not needed anyway.
        replace_in_file(self, os.path.join(self.source_folder, "Cbc", "Makefile.in"), " install-data-am", "")
        autotools.configure(build_script_folder="Cbc")
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Installation script expects include/coin to already exist
        mkdir(self, os.path.join(self.package_folder, "include", "coin"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.components["libcbc"].set_property("pkg_config_name", "cbc")
        self.cpp_info.components["libcbc"].libs = ["Cbc"]
        self.cpp_info.components["libcbc"].includedirs.append("include/coin")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libcbc"].system_libs = ["m", "pthread", "rt", "dl"]
        self.cpp_info.components["libcbc"].requires = [
            "coin-utils::coin-utils",
            "coin-osi::coin-osi",
            "coin-cgl::coin-cgl",
            "coin-clp::osi-clp",
        ]
        if self.options.with_nauty:
            self.cpp_info.components["libcbc"].requires.append("nauty::nauty")
        if self.options.with_dylp:
            self.cpp_info.components["libcbc"].requires.append("coin-dylp::coin-dylp")
        if self.options.with_vol:
            self.cpp_info.components["libcbc"].requires.append("coin-vol::coin-vol")
        if self.options.parallel and self.settings.os == "Windows":
            self.cpp_info.components["libcbc"].requires.append("pthreads4w::pthreads4w")

        self.cpp_info.components["solver"].set_property("pkg_config_name", "cbcsolver")  # unofficial
        self.cpp_info.components["solver"].libs = ["CbcSolver"]
        self.cpp_info.components["solver"].requires = ["libcbc"]
        if self.options.with_asl:
            self.cpp_info.components["solver"].requires.append("ampl-asl::asl")

        self.cpp_info.components["osi-cbc"].set_property("pkg_config_name", "osi-cbc")
        self.cpp_info.components["osi-cbc"].libs = ["OsiCbc"]
        self.cpp_info.components["osi-cbc"].requires = ["libcbc", "coin-osi::coin-osi"]
