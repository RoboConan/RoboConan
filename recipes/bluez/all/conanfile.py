import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, AutotoolsDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class BluezConan(ConanFile):
    name = "bluez"
    description = "Bluetooth protocol stack for Linux"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.bluez.org/"
    topics = ("bluetooth",)
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_alsa": [True, False],
        "with_jsonc": [True, False],
        "with_systemd": [True, False],
        "with_udev": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_alsa": False,
        "with_jsonc": True,
        "with_systemd": True,
        "with_udev": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.36.0]")
        self.requires("dbus/[^1.10]")
        self.requires("libell/[>=0.76 <1]")
        self.requires("readline/[^8.2]")
        if self.options.with_alsa:
            self.requires("libalsa/[^1.2]")
        if self.options.with_jsonc:
            self.requires("json-c/[>=0.17 <1]")
        if self.options.with_udev:
            self.requires("libudev/[>=255 <system]")
        if self.options.with_systemd:
            self.requires("libsystemd/[^255]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("This recipe only supports Linux.")

    def build_requirements(self):
        self.tool_requires("libtool/[^2.4.7]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[^2.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")

        def opt_enable(what, v):
            return "--{}-{}".format("enable" if v else "disable", what)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            opt_enable("debug", self.settings.build_type == "Debug"),
            opt_enable("library", True),
            opt_enable("tools", False),
            opt_enable("testing", False),
            opt_enable("manpages", False),
            opt_enable("client", False),
            opt_enable("monitor", False),
            opt_enable("external-ell", True),
            opt_enable("cups", False),
            opt_enable("mesh", self.options.with_jsonc),
            opt_enable("midi", self.options.with_alsa),
            opt_enable("obex", False),
            opt_enable("systemd", self.options.with_systemd),
            opt_enable("udev", self.options.with_udev),
            # Match the defaults from https://salsa.debian.org/bluetooth-team/bluez/-/blob/debian/sid/debian/rules
            opt_enable("threads", True),
            opt_enable("nfc", True),
            opt_enable("sap", True),
            opt_enable("sixaxis", True),
            opt_enable("health", True),
            opt_enable("hid2hci", True),
            opt_enable("experimental", True),
            "--with-dbusconfdir=/usr/share",
            "--with-udevdir=/usr/lib/udev",
            "--with-systemdsystemunitdir=/usr/lib/systemd/system",
            "--with-systemduserunitdir=/usr/lib/systemd/user",
        ])
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        # Alternatively, get udev and systemd paths from the system pkg-config.
        # env = Environment()
        # env.define_path("PKG_CONFIG_PATH", self.generators_folder)
        # env.append_path("PKG_CONFIG_PATH", "/usr/share/pkgconfig")
        # env.vars(self).save_script("conan_pkg_config_path")

    def build(self):
        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE.LIB", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "etc"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "usr"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "bluez")
        self.cpp_info.libs = ["bluetooth"]
        self.cpp_info.bindirs.append(os.path.join("libexec", "bluetooth"))
