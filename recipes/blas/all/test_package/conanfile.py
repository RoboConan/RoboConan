import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    @property
    def _has_f77blas(self):
        provider = str(self.dependencies["blas"].options.provider)
        if provider == "openblas":
            return self.dependencies["openblas"].options.get_safe("use_fortran", False)
        if provider == "nvpl":
            return self.dependencies["nvpl_blas"].options.compatibility_headers
        return False

    def generate(self):
        tc = CMakeToolchain(self)
        if self._has_f77blas:
            tc.preprocessor_definitions["HAVE_F77BLAS"] = None
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
