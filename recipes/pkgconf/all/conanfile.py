import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class PkgConfConan(ConanFile):
    name = "pkgconf"
    description = "package compiler and linker metadata toolkit"
    license = "ISC"
    homepage = "https://git.sr.ht/~kaniini/pkgconf"
    topics = ("build", "configuration")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_lib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_lib": False,
    }
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.enable_lib:
            self.options.rm_safe("fPIC")
            self.options.rm_safe("shared")
            self.package_type = "application"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        if not self.info.options.enable_lib:
            del self.info.settings.compiler

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        if Version(self.version) < "3.0.0":
            tc.project_options["tests"] = "disabled"
        if not self.options.enable_lib:
            tc.project_options["default_library"] = "static"
        tc.generate()

    def _patch_sources(self):
        if not self.options.get_safe("shared", False):
            replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                            "'-DLIBPKGCONF_EXPORT'",
                            "'-DPKGCONFIG_IS_STATIC'")
            if Version(self.version) < "3.0.0":
                replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                                "project('pkgconf', 'c',",
                                "project('pkgconf', 'c',\ndefault_options : ['c_std=gnu99'],")

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder,"licenses"))
        meson = Meson(self)
        meson.install()

        rm(self, "*.pdb", self.package_folder, recursive=True)

        if not self.options.enable_lib:
            rmdir(self, os.path.join(self.package_folder, "lib"))
            rmdir(self, os.path.join(self.package_folder, "include"))

        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        if self.options.enable_lib:
            self.cpp_info.set_property("pkg_config_name", "libpkgconf")
            self.cpp_info.includedirs.append(os.path.join("include", "pkgconf"))
            self.cpp_info.libs = ["pkgconf"]
            if not self.options.shared:
                self.cpp_info.defines = ["PKGCONFIG_IS_STATIC"]
            else:
                self.cpp_info.defines = ["PKGCONFIG_IS_NOT_STATIC"]
        else:
            self.cpp_info.includedirs = []
            self.cpp_info.libdirs = []

        self.cpp_info.resdirs = ["share"]

        exesuffix = ".exe" if self.settings.os == "Windows" else ""
        pkg_config = os.path.join(self.package_folder, "bin", "pkgconf" + exesuffix).replace("\\", "/")
        self.buildenv_info.define_path("PKG_CONFIG", pkg_config)

        pkgconf_aclocal = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.append_path("ACLOCAL_PATH", pkgconf_aclocal)

        # To ensure that PkgConfig(self, "<lib>").variables uses the correct executable
        if not self.conf.get("tools.gnu:pkg_config", default=False):
            self.conf_info.define("tools.gnu:pkg_config", pkg_config)
