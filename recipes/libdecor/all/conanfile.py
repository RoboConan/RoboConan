import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class libdecorConan(ConanFile):
    name = "libdecor"
    description = "libdecor is a library that can help Wayland clients draw window decorations for them."
    topics = ("decoration", "wayland", "window")
    homepage = "https://gitlab.freedesktop.org/libdecor/libdecor"
    license = "MIT"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_dbus": [True, False],
        "with_gtk": [True, False],
    }
    default_options = {
        "with_dbus": False,
        "with_gtk": False,
    }

    implements = ["auto_shared_fpic"]
    languages = "C"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("wayland/[^1.22.0]", transitive_headers=True)
        self.requires("pango/[^1.54.0]")
        if self.options.with_dbus:
            self.requires("dbus/[^1.15]")
        if self.options.with_gtk:
            self.requires("gtk/[^3.24]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} only supports Linux")
        if not self.dependencies["pango"].options.with_cairo:
            raise ConanInvalidConfiguration(f"{self.ref} requires the with_cairo option of pango to be enabled")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("wayland/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        def feature(option):
            return "enabled" if self.options.get_safe(option) else "disabled"

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["dbus"] = feature("with_dbus")
        tc.project_options["demo"] = False
        tc.project_options["gtk"] = feature("with_gtk")
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        libdecor_soversion = "0"
        self.cpp_info.set_property("pkg_config_name", f"libdecor-{libdecor_soversion}")
        self.cpp_info.libs = [f"decor-{libdecor_soversion}"]
        self.cpp_info.includedirs = [os.path.join("include", f"libdecor-{libdecor_soversion}")]

        plugins_soversion = "1"
        self.runenv_info.append_path("LIBDECOR_PLUGIN_DIR", os.path.join(self.package_folder, "lib", "libdecor", f"plugins-{plugins_soversion}"))
