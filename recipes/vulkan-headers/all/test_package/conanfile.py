import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.scm import Version


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    # CMake 4.4's opt-in token from Help/dev/experimental.rst.
    _cmake_import_std_uuid = "f35a9ac6-8463-4d38-8eec-5d6008153e7d"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("cmake/[~4.4.0]")
        self.tool_requires("ninja/[^1.11]")

    def generate(self):
        dependency = self.dependencies["vulkan-headers"]
        module = dependency.options.get_safe("module", False)
        tc = CMakeToolchain(self, generator="Ninja" if module else None)
        tc.cache_variables["TEST_VULKAN_HPP_MODULE"] = module
        if module and Version(dependency.ref.version) >= "1.4.363":
            tc.cache_variables["CMAKE_EXPERIMENTAL_CXX_IMPORT_STD"] = self._cmake_import_std_uuid
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
            if self.dependencies["vulkan-headers"].options.get_safe("module"):
                self.run(f"{bin_path}_module", env="conanrun")
