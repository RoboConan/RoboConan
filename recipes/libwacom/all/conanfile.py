import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class LibwacomConan(ConanFile):
    name = "libwacom"
    description = "libwacom is a library to identify graphics tablets and their model-specific features."
    license = "MIT"
    homepage = "https://github.com/linuxwacom/libwacom"
    topics = ("device", "graphics", "input", "tablet", "wacom")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]")
        self.requires("libgudev/238")
        self.requires("libevdev/1.13.1")

    def validate(self):
        if not self.settings.os in ["FreeBSD", "Linux"]:
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on {self.settings.os}.")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["documentation"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.generate()
        tc = PkgConfigDeps(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libwacom")
        self.cpp_info.libs = ["wacom"]
        self.cpp_info.includedirs = [os.path.join(self.package_folder, "include", "libwacom-1.0")]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "libgudev::libgudev",
            "libevdev::libevdev",
        ]
        self.runenv_info.append_path("LIBWACOM_DATA_DIR", os.path.join(self.package_folder, "share", "libwacom"))
