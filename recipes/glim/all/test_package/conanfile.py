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

    def generate(self):
        opts = self.dependencies["glim"].options
        tc = CMakeToolchain(self)
        tc.variables["GLIM_WITH_CUDA"] = opts.cuda
        tc.variables["GLIM_WITH_VIEWER"] = opts.viewer
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        resource_dir = self.dependencies["glim"].cpp_info.aggregated_components().resdirs[0]
        assert os.path.isfile(os.path.join(resource_dir, "config.json"))
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(f'"{bin_path}" "{resource_dir}"', scope="run")
