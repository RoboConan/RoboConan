import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class Libdc1394Conan(ConanFile):
    name = "libdc1394"
    license = "LGPL-2.1-or-later"
    homepage = "https://damien.douxchamps.net/ieee1394/libdc1394/"
    description = "libdc1394 provides a complete high level API to control IEEE 1394 based cameras"
    topics = ("ieee1394", "camera", "iidc", "dcam")
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
        self.requires("libusb/[^1.0.26]")
        if self.settings.os == "Linux":
            self.requires("libraw1394/2.1.2")
        elif self.settings.os == "Windows":
            # TODO: requires lib1394camera from https://www.cs.cmu.edu/~iwan/1394/downloads/index.html
            pass

    def validate(self):
        if self.info.settings.os == "Windows":
            raise ConanInvalidConfiguration("Windows support requires lib1394camera, which is not yet available")
        if self.info.settings.compiler == "clang":
            raise ConanInvalidConfiguration("Clang doesn't support VLA")

    def build_requirements(self):
        self.tool_requires("gnu-config/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        for gnu_config in [
            self.conf.get("user.gnu-config:config_guess", check_type=str),
            self.conf.get("user.gnu-config:config_sub", check_type=str),
        ]:
            if gnu_config:
                copy(self, os.path.basename(gnu_config), src=os.path.dirname(gnu_config), dst=self.source_folder)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-examples")
        # Disable auto-detection of X11 and SDL dependencies
        tc.configure_args.append("--without-x")
        tc.configure_args.append("SDL_CONFIG=/dev/null")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", f"libdc1394-{Version(self.version).major}")
        self.cpp_info.libs = ["dc1394"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        elif is_apple_os(self):
            self.cpp_info.frameworks.extend(["CoreFoundation", "CoreServices", "IOKit"])
