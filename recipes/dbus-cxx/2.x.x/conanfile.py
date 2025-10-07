import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeDeps, cmake_layout, CMake, CMakeToolchain
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class DbusCXX(ConanFile):
    name = "dbus-cxx"
    description = "DBus-cxx provides an object-oriented interface to DBus"
    license = "LGPL-3.0-only OR BSD-3-Clause"
    homepage = "http://dbus-cxx.github.io"
    topics = "bus", "interprocess", "message"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "with_glib": [True, False],
        "with_qt": [True, False],
        "with_uv": [True, False],
    }
    # Default to a relocatable static library with only the default
    # standalone dispatcher
    default_options = {
        "fPIC": True,
        "with_glib": False,
        "with_qt": False,
        "with_uv": False,
    }

    def requirements(self):
        self.requires("libsigcpp/[^3.0.7]", transitive_headers=True)
        if self.options.get_safe("with_glib"):
            self.requires("glib/[^2.70.0]", transitive_headers=True)
        if self.options.get_safe("with_uv"):
            self.requires("libuv/[>=1 <2]", transitive_headers=True)
        if self.options.with_qt:
            self.requires("qt/[~5.15]", transitive_headers=True)

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("This library only supports Linux.")
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["ENABLE_CODE_COVERAGE_REPORT"] = False
        tc.cache_variables["ENABLE_EXAMPLES"] = False
        tc.cache_variables["ENABLE_TOOLS"] = False  # note: requires expat lib
        tc.cache_variables["BUILD_SITE"] = False
        tc.cache_variables["ENABLE_GLIB_SUPPORT"] = self.options.with_glib
        tc.cache_variables["ENABLE_QT_SUPPORT"] = self.options.with_qt
        tc.cache_variables["ENABLE_UV_SUPPORT"] = self.options.with_uv

        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # remove useless folders
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        # dbus-cxx
        self.cpp_info.components["dbus-cxx"].libs = ["dbus-cxx"]
        self.cpp_info.components["dbus-cxx"].requires = ["libsigcpp::libsigcpp"]
        self.cpp_info.components["dbus-cxx"].includedirs = ['include/dbus-cxx-2.0']
        self.cpp_info.components["dbus-cxx"].set_property("cmake_target_name", "dbus-cxx")
        self.cpp_info.components["dbus-cxx"].set_property("pkg_config_name", "dbus-cxx-2.0")
        # dbus-cxx-glib
        if self.options.with_glib:
            self.cpp_info.components["dbus-cxx-glib"].libs = ["dbus-cxx-glib"]
            self.cpp_info.components["dbus-cxx-glib"].requires = ["dbus-cxx", "libsigcpp::libsigcpp", "glib::glib-2.0"]
            self.cpp_info.components["dbus-cxx-glib"].includedirs = ['include/dbus-cxx-glib-2.0']
            self.cpp_info.components["dbus-cxx-glib"].set_property("cmake_target_name", "dbus-cxx-glib")
            self.cpp_info.components["dbus-cxx-glib"].set_property("pkg_config_name", "dbus-cxx-glib-2.0")
        # dbus-cxx-qt
        if self.options.with_qt:
            self.cpp_info.components["dbus-cxx-qt"].libs = ["dbus-cxx-qt"]
            self.cpp_info.components["dbus-cxx-qt"].requires = ["dbus-cxx", "libsigcpp::libsigcpp", "qt::qtCore"]
            self.cpp_info.components["dbus-cxx-qt"].includedirs = ['include/dbus-cxx-qt-2.0']
            self.cpp_info.components["dbus-cxx-qt"].set_property("cmake_target_name", "dbus-cxx-qt")
            self.cpp_info.components["dbus-cxx-qt"].set_property("pkg_config_name", "dbus-cxx-qt-2.0")
        # dbus-cxx-uv
        if self.options.get_safe("with_uv"):
            self.cpp_info.components["dbus-cxx-uv"].libs = ["dbus-cxx-uv"]
            self.cpp_info.components["dbus-cxx-uv"].requires = ["dbus-cxx", "libsigcpp::libsigcpp", "libuv::libuv"]
            self.cpp_info.components["dbus-cxx-uv"].includedirs = ['include/dbus-cxx-uv-2.0']
            self.cpp_info.components["dbus-cxx-uv"].set_property("cmake_target_name", "dbus-cxx-uv")
            self.cpp_info.components["dbus-cxx-uv"].set_property("pkg_config_name", "dbus-cxx-uv-2.0")
