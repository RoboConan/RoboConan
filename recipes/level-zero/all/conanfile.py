import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.files import *


class LevelZeroConan(ConanFile):
    name = "level-zero"
    description = "OneAPI Level Zero Specification Headers and Loader"
    license = "MIT"
    homepage = "https://github.com/oneapi-src/level-zero"
    topics = ("api-headers", "loader", "level-zero", "oneapi")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if is_apple_os(self):
            self.output.warning("Level Zero is not known to support Apple platforms")
        if self.settings.os == "Windows" and self.settings.get_safe("subsystem") == "uwp":
            raise ConanInvalidConfiguration(f"{self.ref} does not support UWP on Windows.")
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 14)", "")
        replace_in_file(self, "source/loader/ze_loader.cpp",
                        "#ifdef __linux__",
                        "#if defined(__linux__) || defined(__APPLE__)")
        save(self, "samples/CMakeLists.txt", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_L0_LOADER_TESTS"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "level-zero")

        self.cpp_info.components["ze-loader"].set_property("pkg_config_name", "libze_loader")
        self.cpp_info.components["ze-loader"].libs = ["ze_loader"]
        self.cpp_info.components["ze-loader"].includedirs = ["include", "include/level_zero"]
