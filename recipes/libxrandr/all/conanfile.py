import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class LibXrandrConan(ConanFile):
    name = "libxrandr"
    description = "libXrandr: Xlib Resize, Rotate and Reflection (RandR) extension library"
    license = "HPND-sell-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxrandr"
    topics = ("xorg", "x11")

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
        self.requires("xorg-proto/[>=2024.1]", transitive_headers=True)
        self.requires("libx11/[^1.8.13]")
        self.requires("libxext/[^1.3.7]")
        self.requires("libxrender/[>=0.9.12 <1]", transitive_headers=True)

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported.")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        self.tool_requires("meson/[>=1.1.0 <2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "xrandr")
        self.cpp_info.set_property("cmake_target_name", "X11::Xrandr")
        self.cpp_info.libs = ["Xrandr"]
        self.cpp_info.requires = [
            "xorg-proto::xorg-proto",
            "libx11::x11",
            "libxext::libxext",
            "libxrender::libxrender",
        ]
