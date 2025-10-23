import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import cross_building
from conan.tools.files import *
from conan.tools.gnu import Autotools, GnuToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class FlexConan(ConanFile):
    name = "flex"
    homepage = "https://github.com/westes/flex"
    description = "Flex, the fast lexical analyzer generator"
    topics = ("lex", "lexer", "lexical analyzer generator")
    license = "BSD-2-Clause"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Flex requires M4 to be compiled. If consumer does not have M4
        # installed, Conan will need to know that Flex requires it.
        self.requires("m4/[^1.4.20]")

    def build_requirements(self):
        self.tool_requires("m4/<host_version>")
        self.tool_requires("gnu-config/[*]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if cross_building(self):
            self.tool_requires(f"{self.name}/{self.version}")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("Flex package is not compatible with Windows. "
                                            "Consider using winflexbison instead.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = GnuToolchain(self)
        tc.configure_args["--enable-nls"] = "yes" if self.options.i18n else "no"
        tc.configure_args["--disable-bootstrap"] = None
        tc.configure_args["HELP2MAN"] = "/bin/true"
        tc.configure_args["M4"] = "m4"
        # https://github.com/westes/flex/issues/247
        tc.configure_args["ac_cv_func_malloc_0_nonnull"] = "yes"
        tc.configure_args["ac_cv_func_realloc_0_nonnull"] = "yes"
        # https://github.com/easybuilders/easybuild-easyconfigs/pull/5792
        tc.configure_args["ac_cv_func_reallocarray"] = "no"
        if is_apple_os(self):
            tc.configure_args["-headerpad_max_install_names"] = None
        env = tc.extra_env
        env_vars = env.vars(self)
        # flex looks for build-context CC even if not cross-compiling
        env.define_path("CC_FOR_BUILD", env_vars.get("CC_FOR_BUILD", env_vars.get("CC", "cc")))
        tc.generate()

    def _patch_sources_autotools(self):
        for gnu_config in [
            self.conf.get("user.gnu-config:config_guess", check_type=str),
            self.conf.get("user.gnu-config:config_sub", check_type=str),
        ]:
            if gnu_config:
                copy(self, os.path.basename(gnu_config),
                     src=os.path.dirname(gnu_config),
                     dst=os.path.join(self.source_folder, "config"))

    def build(self):
        self._patch_sources_autotools()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "share", "info"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.libs = ["fl"]
        self.cpp_info.system_libs = ["m"]
        # Avoid CMakeDeps messing with Conan targets
        self.cpp_info.set_property("cmake_find_mode", "none")

        lex_path = os.path.join(self.package_folder, "bin", "flex")
        self.runenv_info.define_path("LEX", lex_path)
