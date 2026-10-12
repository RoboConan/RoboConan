import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.dependencies["uno"].options.with_mumps:
            tc.preprocessor_definitions["TEST_UNO_MUMPS"] = None
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
            if self.settings.os in ["Linux", "FreeBSD", "Macos"]:
                dlopen_path = os.path.join(self.cpp.build.bindir, "test_dlopen")
                self.run(dlopen_path, env="conanrun")
            c_api_bin_path = os.path.join(self.cpp.build.bindir, "test_c_api")
            self.run(c_api_bin_path, env="conanrun")
