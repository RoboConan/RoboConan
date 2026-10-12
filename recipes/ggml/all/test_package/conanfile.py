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
        tc = CMakeToolchain(self)
        options = self.dependencies[self.tested_reference_str].options
        for option, name in (
            ("cpu", "CPU"),
            ("with_blas", "BLAS"),
            ("with_cuda", "CUDA"),
            ("with_metal", "METAL"),
            ("with_opencl", "OPENCL"),
            ("with_rpc", "RPC"),
            ("with_sycl", "SYCL"),
            ("with_vulkan", "VULKAN"),
        ):
            if options.get_safe(option, False):
                tc.preprocessor_definitions[f"GGML_TEST_{name}"] = 1
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
