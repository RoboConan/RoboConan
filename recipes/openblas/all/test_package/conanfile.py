import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain
from conan.tools.microsoft import is_msvc


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        dependency = self.dependencies["openblas"]
        tc = CMakeToolchain(self)
        suffix = "64" if dependency.options.interface == "ilp64" else ""
        tc.cache_variables["OPENBLAS_CMAKE_PACKAGE"] = f"OpenBLAS{suffix}"
        tc.cache_variables["OPENBLAS_CMAKE_TARGET"] = f"OpenBLAS{suffix}::OpenBLAS"
        compatibility_targets = [f"OpenBLAS::{dependency.options.threading}"]
        if suffix:
            compatibility_targets.extend(["OpenBLAS::OpenBLAS", "OpenBLAS::OpenBLAS64"])
        tc.cache_variables["OPENBLAS_COMPATIBILITY_TARGETS"] = ";".join(compatibility_targets)
        if dependency.options.build_lapack:
            tc.preprocessor_definitions["OPENBLAS_TEST_LAPACKE"] = None
        if dependency.options.get_safe("use_fortran", False):
            tc.preprocessor_definitions["OPENBLAS_TEST_FORTRAN"] = None
            tc.cache_variables["OPENBLAS_TEST_INTEL_FORTRAN_ALIASES"] = is_msvc(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
