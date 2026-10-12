import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.scm import Version


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["TEST_ONNX_NAMESPACED_TARGETS"] = (
            Version(self.dependencies["onnx"].ref.version) >= "1.16.0"
        )
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            for executable in ("test_package", "test_package_proto"):
                bin_path = os.path.join(self.cpp.build.bindir, executable)
                self.run(bin_path, env="conanrun")
