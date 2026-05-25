import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class CtreConan(ConanFile):
    name = "ctre"
    description = "Compile Time Regular Expression for C++17/20"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/hanickadot/compile-time-regular-expressions"
    topics = ("cpp17", "regex", "compile-time-regular-expressions", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.19]")

    def validate(self):
        check_min_cppstd(self, 17)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CTRE_BUILD_TESTS"] = False
        tc.cache_variables["CTRE_BUILD_PACKAGE"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version],  strip_root=True)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkg-config"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
