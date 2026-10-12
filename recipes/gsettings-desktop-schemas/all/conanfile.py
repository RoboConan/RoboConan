import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class GsettingsDesktopSchemasConan(ConanFile):
    name = "gsettings-desktop-schemas"
    description = "A collection of GSettings schemas for settings shared by various components of a desktop."
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gsettings-desktop-schemas"
    topics = ("gnome", "gsettings", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_introspection": [True, False],
        "i18n": [True, False],
    }
    default_options = {
        "with_introspection": False,
        "i18n": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def configure(self):
        if self.options.with_introspection:
            self.package_type = "shared-library"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        if not self.info.options.with_introspection:
            self.info.clear()

    def requirements(self):
        if self.options.with_introspection:
            self.requires("gobject-introspection/[^1.82]")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["introspection"] = self.options.with_introspection
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        if not self.options.i18n:
            save(self, os.path.join(self.source_folder, "po", "meson.build"), "")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "share", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "gsettings-desktop-schemas")
        self.cpp_info.includedirs = [os.path.join("include", "gsettings-desktop-schemas")]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        if self.options.with_introspection:
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
