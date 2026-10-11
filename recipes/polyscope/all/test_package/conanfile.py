import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        dependency = self.dependencies[self.tested_reference_str]
        tc = CMakeToolchain(self)
        if dependency.options.backend_glfw:
            tc.preprocessor_definitions["POLYSCOPE_TEST_BACKEND_GLFW"] = 1
        if dependency.options.get_safe("backend_egl", False):
            tc.preprocessor_definitions["POLYSCOPE_TEST_BACKEND_EGL"] = 1
        if dependency.options.backend_mock:
            tc.preprocessor_definitions["POLYSCOPE_TEST_BACKEND_MOCK"] = 1
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, scope="run")
