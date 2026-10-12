import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeDeps, CMakeToolchain


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        integer8 = self.dependencies["blas"].options.interface == "ilp64"
        tc = CMakeToolchain(self)
        tc.cache_variables["TEST_SLICOT_INTEGER8"] = integer8
        if integer8:
            tc.preprocessor_definitions["TEST_SLICOT_INTEGER8"] = None
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
