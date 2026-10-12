import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class TslibConan(ConanFile):
    name = "tslib"
    description = "C library for filtering touchscreen events"
    license = "LGPL-2.1-only"
    homepage = "http://www.tslib.org/"
    topics = ("touch-devices", "touchscreen", "embedded")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "with_libevdev": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "with_libevdev": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_libevdev:
            self.requires("libevdev/1.13.1")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 3.3)",
                        "cmake_minimum_required(VERSION 3.5)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_TOOLS"] = self.options.tools
        tc.cache_variables["enable-input-evdev"] = self.options.with_libevdev
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tslib")
        self.cpp_info.set_property("cmake_target_name", "tslib::tslib")
        self.cpp_info.set_property("pkg_config_name", "tslib")

        self.cpp_info.libs = ["ts"]

        self.runenv_info.define_path("TSLIB_PLUGINDIR", os.path.join(self.package_folder, "lib", "ts"))
        self.runenv_info.define_path("TSLIB_CALIBFILE", os.path.join(self.package_folder, "etc", "pointercal"))
        self.runenv_info.define_path("TSLIB_CONFFILE", os.path.join(self.package_folder, "etc", "ts.conf"))

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "dl"])
