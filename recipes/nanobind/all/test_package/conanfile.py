import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain, CMakeDeps


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("cpython/[^3.10]")

    def build_requirements(self):
        self.tool_requires("cpython/<host_version>")
        self.tool_requires("cmake/[^4.4]")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["Python_EXECUTABLE"] = os.path.join(
            self.dependencies.build["cpython"].package_folder, "bin", "python"
        ).replace("\\", "/")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            modules = ["test_package_static", "test_package_shared"]
            if self.dependencies[self.tested_reference_str].ref.version.major >= "3":
                modules.append("test_package_split")
            imports = "; ".join(f"import {module}; assert {module}.add(2, 3) == 5" for module in modules)
            self.run(f'python -c "{imports}"',
                     env="conanrun", cwd=self.cpp.build.bindir)
