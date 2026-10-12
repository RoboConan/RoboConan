import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain
from conan.tools.files import *


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        if self.dependencies["onnxruntime"].options.with_cuda.value in ["full", "minimal"]:
            tc.preprocessor_definitions["WITH_CUDA"] = 1
        tc.generate()
        if self.settings.os == "Windows":
            # on windows the system dll C:\WINDOWS\system32\onnxruntime.dll may be loaded instead even if the conan lib is first in the PATH, see https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order
            for bindir in self.dependencies[self.tested_reference_str].cpp_info.bindirs:
                copy(self, "*.dll", bindir, os.path.join(self.build_folder, str(self.settings.build_type)))

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
