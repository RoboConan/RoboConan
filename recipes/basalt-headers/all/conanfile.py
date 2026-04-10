import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class BasaltConan(ConanFile):
    name = "basalt-headers"
    description = "Reusable components of Basalt as a header-only library"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.com/VladyslavUsenko/basalt-headers"
    topics = ("computer-vision", "slam", "vio", "calibration", "b-splines")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def package_id(self):
        self.info.clear()

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[^5]")
        self.requires("sophus/[^1]")
        self.requires("cereal/[^1.3]")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["CXX_MARCH"] = ""
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "basalt-headers")
        self.cpp_info.set_property("cmake_target_name", "basalt::basalt-headers")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
