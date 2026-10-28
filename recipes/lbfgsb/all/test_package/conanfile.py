import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type", "fortran"
    generators = "CMakeDeps"
    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        mangling = self.fortran.mangling
        if mangling.case == "upper":
            symbol = "DNRM2"
        elif mangling.underscore:
            symbol = "dnrm2_"
        else:
            symbol = "dnrm2"
        tc.preprocessor_definitions["TEST_DNRM2"] = symbol
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
