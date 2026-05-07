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


class LibXawConan(ConanFile):
    name = "libxaw"
    description = "libXaw: X Athena Widget Set, based on the X Toolkit Intrinsics (Xt) Library"
    license = "MIT-open-group AND X11 AND HPND AND HPND-sell-variant AND SMLNJ AND NTP"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxaw"
    topics = ("xorg", "x11")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_xaw6": [True, False],
        "build_xaw7": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_xaw6": False,
        "build_xaw7": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("xorg-proto/[>=2024.1]", transitive_headers=True)
        self.requires("libx11/[^1.8.13]", transitive_headers=True)
        self.requires("libxt/[^1.3.1]", transitive_headers=True)
        self.requires("libxmu/[^1.3.1]", transitive_headers=True)
        self.requires("libxext/[^1.3.7]")
        if self.options.build_xaw7:
            self.requires("libxpm/[^3.5.17]")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported.")
        if not self.options.build_xaw6 and not self.options.build_xaw7:
            raise ConanInvalidConfiguration("At least one of 'build_xaw6' or 'build_xaw7' must be True.")

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
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        tc.configure_args.extend([
            f"--enable-xaw6={yes_no(self.options.build_xaw6)}",
            f"--enable-xaw7={yes_no(self.options.build_xaw7)}",
        ])
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
        self.cpp_info.set_property("cmake_target_name", "X11::SM")

        if self.options.build_xaw7:
            self.cpp_info.components["xaw7"].set_property("pkg_config_name", "xaw7")
            self.cpp_info.components["xaw7"].set_property("cmake_target_name", "X11::Xaw")
            self.cpp_info.components["xaw7"].libs = ["Xaw7"]
            self.cpp_info.components["xaw7"].requires = [
                "xorg-proto::xorg-proto",
                "libx11::x11",
                "libxext::libxext",
                "libxt::libxt",
                "libxmu::libxmu",
                "libxpm::libxpm",
            ]
            if self.settings.os == "Windows":
                self.cpp_info.components["xaw7"].system_libs = ["ws2_32"]

        if self.options.build_xaw6:
            self.cpp_info.components["xaw6"].set_property("pkg_config_name", "xaw6")
            if not self.options.build_xaw7:
                self.cpp_info.components["xaw6"].set_property("cmake_target_name", "X11::Xaw")
            self.cpp_info.components["xaw6"].libs = ["Xaw6"]
            self.cpp_info.components["xaw6"].requires = [
                "xorg-proto::xorg-proto",
                "libx11::x11",
                "libxext::libxext",
                "libxt::libxt",
                "libxmu::libxmu",
            ]
            if self.settings.os == "Windows":
                self.cpp_info.components["xaw6"].system_libs = ["ws2_32"]
