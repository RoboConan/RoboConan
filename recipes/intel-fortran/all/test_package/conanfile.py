import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type", "fortran"
    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def requirements(self):
        self.fortran.requires_runtime()

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run(os.path.join(self.cpp.build.bindir, "test_package"), env="conanrun")
