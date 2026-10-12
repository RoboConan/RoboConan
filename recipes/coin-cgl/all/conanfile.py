import os
import shutil

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, unix_path

required_conan_version = ">=2.1"


class CoinCglConan(ConanFile):
    name = "coin-cgl"
    description = "COIN-OR Cut Generator Library"
    topics = ("cgl", "simplex", "solver", "linear", "programming")
    homepage = "https://github.com/coin-or/Cgl"
    license = "EPL-2.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_dylp": [True, False],
        "with_vol": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_dylp": True,
        "with_vol": True,
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
        self.requires("coin-osi/[>=0.108.10 <1]")
        self.requires("coin-clp/[^1.17.9]")
        if self.options.with_dylp:
            self.requires("coin-dylp/[^1.10.4]")
        if self.options.with_vol:
            self.requires("coin-vol/[^1.5.4]")

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

    def generate(self):
        yes_no = lambda v: "yes" if v else "no"
        osi = self.dependencies["coin-osi"]
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-clp=yes",
            "--with-osiclp=yes",
            f"--with-osidylp={yes_no(self.options.with_dylp)}",
            f"--with-osivol={yes_no(self.options.with_vol)}",
            f"--with-osicplex={yes_no(osi.options.with_cplex)}",
            f"--with-osiglpk={yes_no(osi.options.with_glpk)}",
            f"--with-osigurobi={yes_no(osi.options.with_gurobi)}",
            f"--with-osimosek={yes_no(osi.options.with_mosek)}",
            f"--with-osisoplex={yes_no(osi.options.with_soplex)}"
            f"--with-osixpress={yes_no(osi.options.with_xpress)}",
            "--without-sample",
            "--disable-dependency-linking",
            "F77=unavailable",
        ])
        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
            tc.configure_args.append(f"--enable-msvc={msvc_runtime_flag(self)}")
        env = tc.environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        if is_msvc(self):
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", f"{compile_wrapper} link -nologo")
            env.define("AR", f'{ar_wrapper} "lib -nologo"')
            env.define("NM", "dumpbin -symbols")
        tc.generate(env)

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        copy(self, "*", self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0],
             os.path.join(self.source_folder, "Cgl", "BuildTools"))
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "Cgl"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="Cgl")
        # Fix a failure on Windows. The am data is not needed anyway.
        replace_in_file(self, os.path.join(self.source_folder, "Cgl", "Makefile.in"), " install-data-am", "")
        autotools.configure(build_script_folder="Cgl")
        autotools.make()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "cgl")
        self.cpp_info.libs = ["Cgl"]
        self.cpp_info.includedirs.append("include/coin")
