import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps, AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.4"


class XcbUtilErrorsConan(ConanFile):
    name = "xcb-util-errors"
    description = "XCB utility library that gives human readable names to error, event, & request codes"
    license = "X11-distribute-modifications-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxcb-errors"
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
        self.requires("libxcb/[^1.17.0]", transitive_headers=True, libs=False)

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported.")

    @property
    def _have_python(self):
        return not getattr(sys, "frozen", False)

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        self.tool_requires("m4/[^1.4.20]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        self.tool_requires("xcb-proto/[^1.17.0]")
        if not self._have_python:
            self.tool_requires("cpython/[^3.12]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if not self._have_python:
            python_path = os.path.join(self.dependencies.build["cpython"].cpp_info.bindir, "python3")
            tc.configure_args.append(f"PYTHON={unix_path(self, python_path)}")
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.build_context_activated = ["xcb-proto"]
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
        self.cpp_info.set_property("pkg_config_name", "xcb-errors")
        self.cpp_info.set_property("cmake_target_name", "X11::xcb_errors")
        self.cpp_info.libs = ["xcb-errors"]
        xcbproto_version = self.dependencies.build["xcb-proto"].ref.version
        self.cpp_info.set_property("pkg_config_custom_content", f"xcbproto_version={xcbproto_version}")
        self.cpp_info.requires = ["libxcb::xcb"]
