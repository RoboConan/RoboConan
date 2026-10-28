import os
import shutil

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class CoinDyLPConan(ConanFile):
    name = "coin-dylp"
    description = "Dynamic Linear Programming solver implementing the dynamic simplex algorithm"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/DyLP"
    topics = ("linear-programming", "optimization", "simplex", "coin-or")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_osi": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_osi": True,
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
        if self.options.with_osi:
            self.requires("coin-osi/[>=0.108 <1]", transitive_headers=True)

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
        # Upstream's MSVC fallback contains a stray carriage return, so the
        # subsequent size comparison never matches C char.
        replace_in_file(self, "DyLP/m4/ac_dylp_equiv_for_cpp_bool.m4",
                        'ac_cv_sizeof_cpp_bool="1\r"',
                        'ac_cv_sizeof_cpp_bool="1"')

    def generate(self):
        tc = AutotoolsToolchain(self)
        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
        env = tc.environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        if str(self.settings.compiler) in ["gcc", "clang", "apple-clang"]:
            # The old configure script probes GNU C before initializing the object suffix.
            env.define("ac_cv_c_compiler_gnu", "yes")
        if is_msvc(self):
            ar_wrapper = unix_path(self, self.dependencies.build["automake"].conf_info.get("user.automake:lib-wrapper"))
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("NM", "dumpbin -symbols")
        tc.generate(env)

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        buildtools = self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0]
        copy(self, "*", buildtools, os.path.join(self.source_folder, "DyLP", "BuildTools"))
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "DyLP"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="DyLP")
        # Fix a failure on Windows. The am data is not needed anyway.
        replace_in_file(self, os.path.join(self.source_folder, "DyLP", "Makefile.in"), " install-data-am", "")
        autotools.configure(build_script_folder="DyLP")
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
        self.cpp_info.components["dylp"].set_property("pkg_config_name", "dylp")
        self.cpp_info.components["dylp"].libs = ["Dylp"]
        self.cpp_info.components["dylp"].includedirs.append("include/coin")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["dylp"].system_libs = ["m"]

        if self.options.with_osi:
            self.cpp_info.components["osi-dylp"].set_property("pkg_config_name", "osi-dylp")
            self.cpp_info.components["osi-dylp"].libs = ["OsiDylp"]
            self.cpp_info.components["osi-dylp"].requires = ["dylp", "coin-osi::libosi"]
