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

    def _with_legacy(self):
        return (self.dependencies["openssl"].options.legacy and
            (self.dependencies["openssl"].options.md4 or
              self.dependencies["openssl"].options.rmd160))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["OPENSSL_WITH_LEGACY"] = self._with_legacy()
        tc.cache_variables["OPENSSL_WITH_MD4"] = self.dependencies["openssl"].options.md4
        tc.cache_variables["OPENSSL_WITH_RIPEMD160"] = self.dependencies["openssl"].options.rmd160
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
