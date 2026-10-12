import os
import shutil

from conan import ConanFile
from conan.tools import CppInfo
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps, PkgConfig
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class CoinUtilsConan(ConanFile):
    name = "coin-utils"
    description = (
        "CoinUtils is an open-source collection of classes and helper "
        "functions that are generally useful to multiple COIN-OR projects."
    )
    topics = ("coin-or",)
    homepage = "https://github.com/coin-or/CoinUtils"
    license = "EPL-2.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_glpk": [True, False],
        "with_readline": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_glpk": False,
        "with_readline": False,
    }
    options_description = {
        "with_glpk": "Build with GLPK to add support for the GMPL file format",
        "with_readline": "Build with GNU Readline support",
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
        self.requires("bzip2/[^1.0.8]")
        self.requires("zlib-ng/[^2.0]")
        self.requires("lapack/latest", transitive_headers=True, transitive_libs=True)
        if self.options.with_glpk:
            self.requires("glpk/[>=4 <6]")
        if self.options.with_readline:
            self.requires("readline/[^8.3.1]")

    def build_requirements(self):
        self.tool_requires("coin-buildtools/[*]")
        self.tool_requires("gnu-config/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
            self.tool_requires("automake/[^1.18.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _flags_from_pc(self, name):
        pc = PkgConfig(self, name, self.generators_folder)
        cflags = list(pc.cflags)
        cflags += [f"-I{unix_path(self, inc)}" for inc in pc.includedirs]
        ldflags = list(pc.linkflags)
        ldflags += [f"-L{unix_path(self, libdir)}" for libdir in pc.libdirs]
        ldflags += [f"-l{lib}" for lib in pc.libs]
        return " ".join(cflags), " ".join(ldflags)

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        yes_no = lambda v: "yes" if v else "no"
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--with-glpk={yes_no(self.options.with_glpk)}",
            f"--enable-gnu-packages={yes_no(self.options.with_readline)}",
            "F77=unavailable",
            "ac_cv_f77_mangling=lower case, underscore, no extra underscore",
            # These are only used for sample datasets
            "--without-netlib",
            "--without-sample",
        ])
        if self.settings.os != "Windows":
            tc.configure_args.append("--enable-coinutils-threads")
        if is_msvc(self):
            tc.configure_args.append(f"--enable-msvc={self.settings.compiler.runtime}")
            tc.extra_cxxflags.append("-EHsc")
        env = tc.environment()
        if is_msvc(self):
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f'{ar_wrapper} "lib -nologo"')
            env.define("NM", "dumpbin -symbols")
        tc.generate(env)

        if is_msvc(self):
            # Custom AutotoolsDeps for cl like compilers
            # workaround for https://github.com/conan-io/conan/issues/12784
            cpp_info = CppInfo(self)
            for dependency in reversed(self.dependencies.host.topological_sort.values()):
                cpp_info.merge(dependency.cpp_info.aggregated_components())
            env = Environment()
            env.append("CPPFLAGS", [f"-I{unix_path(self, p)}" for p in cpp_info.includedirs] + [f"-D{d}" for d in cpp_info.defines])
            env.append("_LINK_", [lib if lib.endswith(".lib") else f"{lib}.lib" for lib in cpp_info.libs])
            env.append("LDFLAGS", [f"-L{unix_path(self, p)}" for p in cpp_info.libdirs] + cpp_info.sharedlinkflags + cpp_info.exelinkflags)
            env.append("CXXFLAGS", cpp_info.cxxflags)
            env.append("CFLAGS", cpp_info.cflags)
            env.vars(self).save_script("conanautotoolsdeps_cl_workaround")
        else:
            deps = AutotoolsDeps(self)
            deps.generate()

        deps = PkgConfigDeps(self)
        deps.set_property("blas", "pkg_config_name", "coinblas")
        deps.set_property("lapack", "pkg_config_name", "coinlapack")
        deps.set_property("glpk", "pkg_config_aliases", ["coinglpk"])
        deps.generate()

    def build(self):
        copy(self, "*", self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0],
             os.path.join(self.source_folder, "CoinUtils", "BuildTools"))
        replace_in_file(self, os.path.join(self.source_folder, "CoinUtils", "configure.ac"),
                        "AC_CANONICAL_BUILD",
                        "AC_CANONICAL_BUILD\nAC_CANONICAL_HOST")
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "CoinUtils"))
        mkdir(self, os.path.join(self.build_folder, "src", "lib"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="CoinUtils")
        autotools.configure(build_script_folder="CoinUtils")
        # Manually specify OpenBLAS name mangling since F77 is not available to autodetect it.
        save(self, os.path.join(self.build_folder, "src/config.h"),
             ("\n"
              "#define F77_FUNC(name,NAME) name ## _\n"
              "#define F77_FUNC_(name,NAME) name ## _\n"),
             append=True)
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
        self.cpp_info.set_property("pkg_config_name", "coinutils")
        self.cpp_info.libs = ["CoinUtils" if self.settings.os != "Windows" else "libCoinUtils"]
        self.cpp_info.includedirs.append("include/coin")
        self.cpp_info.requires = [
            "bzip2::bzip2",
            "zlib-ng::zlib-ng",
            "lapack::lapack",
        ]
        if self.options.with_glpk:
            self.cpp_info.requires.append("glpk::glpk")
        if self.options.with_readline:
            self.cpp_info.requires.append("readline::readline")
        if self.settings.os in ["FreeBSD", "Linux"]:
            self.cpp_info.system_libs = ["m", "pthread", "rt"]
