import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class XtransConan(ConanFile):
    name = "xtrans"
    description = "X Network Transport layer shared code"
    license = "HPND AND HPND-sell-variant AND MIT AND MIT-open-group AND X11"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxtrans"
    topics = ("xorg", "x11")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def requirements(self):
        self.requires("xorg-proto/[>=2024.1]")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported.")

    def build_requirements(self):
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
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "xtrans")
        self.cpp_info.defines = ["_DEFAULT_SOURCE", "_BSD_SOURCE", "HAS_FCHOWN", "HAS_STICKY_DIR_BIT"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        # For res/aclocal/xtrans.m4
        aclocal = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.prepend_path("ACLOCAL_PATH", aclocal)
