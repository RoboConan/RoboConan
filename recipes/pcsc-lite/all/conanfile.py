import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class PCSCLiteConan(ConanFile):
    name = "pcsc-lite"
    description = "Middleware to access a smart card using SCard API (PC/SC)"
    license = "BSD-3-Clause AND BSD-2-Clause AND GPL-3.0-or-later"
    homepage = "https://pcsclite.apdu.fr/"
    topics = ("smartcard", "pcsc")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libudev": [True, False],
        "with_libusb": [True, False],
        "usb": [True, False],
        "serial": [True, False],
        "embedded": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libudev": True,
        "with_libusb": False,
        "usb": True,
        "serial": True,
        "embedded": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_libudev:
            self.requires("libudev/[>=255 <system]")
        if self.options.with_libusb:
            self.requires("libusb/[^1.0]")

    def validate(self):
        if self.settings.os not in ["Linux"]:
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on {self.settings.os}.")
        if self.options.with_libudev and self.options.with_libusb:
            raise ConanInvalidConfiguration("with_libudev and with_libusb are mutually exclusive options.")

    def build_requirements(self):
        self.tool_requires("meson/[^1.2.3]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[^2.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["usb"] = self.options.usb
        tc.project_options["serial"] = self.options.serial
        tc.project_options["embedded"] = self.options.embedded
        tc.project_options["libsystemd"] = False
        tc.project_options["libudev"] = self.options.with_libudev
        tc.project_options["libusb"] = self.options.with_libusb
        tc.project_options["polkit"] = False  # polkit-gobject-1 is not available as a Conan package
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
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"), recursive=True)
        else:
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "etc"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libpcsclite")
        self.cpp_info.libs = ["pcsclite"]
        self.cpp_info.includedirs.append(os.path.join("include", "PCSC"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["pthread"])
