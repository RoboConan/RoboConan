import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps, AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class XcbUtilWmConan(ConanFile):
    name = "xcb-util-wm"
    description = "XCB client and window-manager helpers for ICCCM & EWMH"
    license = "X11-distribute-modifications-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxcb-wm"
    topics = ("xorg", "x11", "xcb")

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
        self.requires("libxcb/[^1.17.0]", transitive_headers=True)
        self.requires("xorg-proto/[>=2024.1]")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported.")

    def build_requirements(self):
        self.tool_requires("m4/[^1.4.20]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.components["xcb-icccm"].set_property("pkg_config_name", "xcb-icccm")
        self.cpp_info.components["xcb-icccm"].set_property("cmake_target_name", "X11::xcb_icccm")
        self.cpp_info.components["xcb-icccm"].libs = ["xcb-icccm"]
        self.cpp_info.components["xcb-icccm"].requires = ["libxcb::xcb", "xorg-proto::xorg-proto"]

        self.cpp_info.components["xcb-ewmh"].set_property("pkg_config_name", "xcb-ewmh")
        self.cpp_info.components["xcb-ewmh"].set_property("cmake_target_name", "X11::xcb_ewmh")
        self.cpp_info.components["xcb-ewmh"].libs = ["xcb-ewmh"]
        self.cpp_info.components["xcb-ewmh"].requires = ["libxcb::xcb", "xorg-proto::xorg-proto"]
