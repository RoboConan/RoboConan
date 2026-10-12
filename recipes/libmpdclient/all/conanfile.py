import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibmpdclientConan(ConanFile):
    name = "libmpdclient"
    description = "libmpdclient is a C library which implements the Music Player Daemon protocol."
    license = "BSD-2-Clause", "BSD-3-Clause"
    topics = ("music", "music-player-demon", "sound")
    homepage = "https://www.musicpd.org/libs/libmpdclient"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "default_socket": ["ANY"],
        "default_host": ["ANY"],
        "default_port": ["ANY"],
        "tcp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "default_socket": "/var/run/mpd/socket",
        "default_host": "localhost",
        "default_port": "6600",
        "tcp": True,
    }

    python_requires = "conan-utils/latest"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.default_socket

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if is_msvc(self) and self.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} doesn't support build of shared lib with msvc")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        if self.settings.os != "Windows":
            tc.project_options["default_socket"] = str(self.options.default_socket)
        tc.project_options["default_host"] = str(self.options.default_host)
        tc.project_options["default_port"] = str(self.options.default_port)
        tc.project_options["tcp"] = self.options.tcp
        tc.project_options["documentation"] = False
        tc.project_options["test"] = False
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        if Version(self.version) >= "2.22":
            copy(self, "*", os.path.join(self.source_folder, "LICENSES"), os.path.join(self.package_folder, "licenses"))
        else:
            copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libmpdclient")
        self.cpp_info.libs = ["mpdclient"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("ws2_32")
