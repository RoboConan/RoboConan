import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        resource_dir = self.dependencies["glim_ext"].cpp_info.resdirs[0]
        assert os.path.isfile(os.path.join(resource_dir, "config_ext.json"))
        if self.dependencies["glim_ext"].options.dbow:
            data_dir = self.dependencies["glim_ext"].cpp_info.resdirs[1]
            assert os.path.isfile(os.path.join(data_dir, "orbvoc.dbow3"))
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(f'"{bin_path}" "{resource_dir}"', scope="run")
