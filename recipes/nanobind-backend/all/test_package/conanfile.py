import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("nanobind/[^3.0]")
        self.requires("cpython/[^3.10]")

    def build_requirements(self):
        self.tool_requires("cpython/<host_version>")
        self.tool_requires("cmake/[^4.4]")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["Python_EXECUTABLE"] = os.path.join(self.dependencies.build["cpython"].package_folder, "bin", "python").replace("\\", "/")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            checks = [
                "import nanobind_backend",
                "assert callable(nanobind_backend.fill)",
                "import test_package",
                "assert test_package.add(2, 3) == 5",
            ]
            if self.settings.os != "Windows":
                abi = "abi3t" if self.dependencies["cpython"].options.get_safe("freethreaded") else "abi3"
                checks.append(f"assert '.{abi}.' in test_package.__file__, test_package.__file__")
            script = "; ".join(checks)
            self.run(f'python -B -c "{script}"',
                     env="conanrun", cwd=self.cpp.build.bindir)
