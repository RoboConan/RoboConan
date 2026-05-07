import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class libxftConan(ConanFile):
    name = "libxft"
    description = "X FreeType library"
    license = "HPND-sell-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxft"
    topics = ("x11", "xorg", "freetype")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "use_xorg_system": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "use_xorg_system": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("xorg-proto/[>=2024.1]", transitive_headers=True)
        if self.options.use_xorg_system:
            self.requires("xorg/system", transitive_headers=True)
        else:
            self.requires("libxrender/[>=0.9.12 <1]", transitive_headers=True)
        self.requires("freetype/[^2.13.2]", transitive_headers=True)
        self.requires("fontconfig/[^2.15.0]", transitive_headers=True)

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        self.tool_requires("xorg-macros/[^1.20.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
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
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "xft")
        self.cpp_info.set_property("cmake_target_aliases", ["X11::Xft"])
        self.cpp_info.libs = ["Xft"]
        self.cpp_info.requires = ["xorg-proto::xorg-proto", "freetype::freetype", "fontconfig::fontconfig"]
        if self.options.use_xorg_system:
            self.cpp_info.requires.append("xorg::xrender")
        else:
            self.cpp_info.requires.append("libxrender::libxrender")
