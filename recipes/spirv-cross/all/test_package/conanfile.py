import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str, run=can_run(self))

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            opts = self.dependencies["spirv-cross"].options
            if not opts.get_safe("shared", False):
                bin_path = os.path.join(self.cpp.build.bindir, "test_package_cpp")
                self.run(bin_path, env="conanrun")
            if opts.c_api:
                bin_path = os.path.join(self.cpp.build.bindir, "test_package_c")
                self.run(bin_path, env="conanrun")
            if opts.build_executable:
                self.run("spirv-cross --help", env="conanrun")
