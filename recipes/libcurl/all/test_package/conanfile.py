import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _test_executable(self):
        return os.path.join(self.cpp.build.bindir, "test_package")

    def test(self):
        if self.dependencies[self.tested_reference_str].options.build_executable:
            ext = ".exe" if self.settings.os == "Windows" else ""
            curl = os.path.join(self.dependencies[self.tested_reference_str].cpp_info.bindir, f"curl{ext}")
            assert os.path.exists(curl)

        if can_run(self):
            self.run(self._test_executable, env="conanrun")
            if self.dependencies[self.tested_reference_str].options.build_executable:
                self.run(f'"{curl}" --version', env="conanrun")
