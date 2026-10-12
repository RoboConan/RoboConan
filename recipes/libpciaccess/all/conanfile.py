import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson

required_conan_version = ">=2.4"


class LibPciAccessConan(ConanFile):
    name = "libpciaccess"
    description = "Generic PCI access library"
    license = "MIT AND ISC AND X11"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libpciaccess"
    topics = ("pci", "xorg")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")

    def validate(self):
        def is_supported(settings):
            if settings.os in ("Linux", "FreeBSD", "SunOS"):
                return True
            return settings.os == "Windows" and settings.get_safe("os.subsystem") == "cygwin"
        if not is_supported(self.settings):
            raise ConanInvalidConfiguration("Unsupported architecture.")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("xorg-macros/1.20.2")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        autotools = Meson(self)
        autotools.configure()
        autotools.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Meson(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["pciaccess"]
        self.cpp_info.set_property("pkg_config_name", "pciaccess")
