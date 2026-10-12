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
        gtsam = self.dependencies["gtsam"]
        tc = CMakeToolchain(self)
        tc.variables["TEST_CXX_STANDARD"] = 17 if Version(gtsam.ref.version, qualifier=True) >= "4.3" else 11
        tc.variables["TEST_CEPHES"] = Version(gtsam.ref.version, qualifier=True) >= "4.3"
        tc.variables["TEST_BOOST_SERIALIZATION"] = gtsam.options.get_safe("enable_boost_serialization", True)
        tc.variables["TEST_CPPUNITLITE"] = gtsam.options.install_cppunitlite
        tc.variables["TEST_CUDA"] = gtsam.options.get_safe("with_cuda", False)
        tc.variables["TEST_CUDSS"] = gtsam.options.get_safe("with_cudss", False)
        tc.variables["TEST_METIS"] = Version(gtsam.ref.version, qualifier=True) >= "4.3" and gtsam.options.support_nested_dissection
        tc.variables["TEST_MKL"] = gtsam.options.get_safe("with_mkl", False)
        tc.variables["TEST_MOSEK"] = gtsam.options.get_safe("with_mosek", False)
        tc.variables["TEST_UNSTABLE"] = gtsam.options.build_unstable
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
