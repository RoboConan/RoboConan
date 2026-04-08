import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class LibgudevConan(ConanFile):
    name = "libgudev"
    description = "GObject bindings for libudev"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgudev/"
    topics = ("udev", "gobject")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_introspection": False,
    }
    languages = ["C"]
    implements = ["auto_shared_fpic"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libudev/[>=255 <system]")
        self.requires("glib/[^2.70.0]", transitive_headers=True)
        if self.options.with_introspection:
            self.requires("glib-gir/[^2.82]")

    def validate(self):
        if self.options.with_introspection and not self.options.shared:
            raise ConanInvalidConfiguration("with_introspection=True requires -o shared=True")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        self.tool_requires("pkgconf/[>=2.2 <3]")
        self.tool_requires("glib/<host_version>")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["vapi"] = "disabled"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["introspection"] = "enabled" if self.options.with_introspection else "disabled"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, pattern="COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "gudev-1.0")
        self.cpp_info.libs = ["gudev-1.0"]
        self.cpp_info.includedirs = [os.path.join("include", "gudev-1.0")]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "libudev::libudev",
        ]
        if self.options.with_introspection:
            self.cpp_info.resdirs = ["share"]
            self.cpp_info.requires.append("glib-gir::glib-gir")
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
