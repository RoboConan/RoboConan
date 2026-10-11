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
        tested_options = self.dependencies[self.tested_reference_str].options
        tc = CMakeToolchain(self)
        tc.variables["WITH_TBBMALLOC"] = tested_options.tbbmalloc
        tc.variables["WITH_TBBPROXY"] = tested_options.get_safe("tbbproxy", False)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            tested_options = self.dependencies[self.tested_reference_str].options
            executables = ["test_package"]
            if tested_options.tbbmalloc:
                executables.append("test_tbbmalloc")
            if tested_options.get_safe("tbbproxy", False):
                executables.append("test_tbbmalloc_proxy")
            for executable in executables:
                bin_path = os.path.join(self.cpp.build.bindir, executable)
                self.run(bin_path, env="conanrun")
