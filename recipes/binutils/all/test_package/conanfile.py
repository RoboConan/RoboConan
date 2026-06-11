import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    @property
    def _has_as(self):
        return self.settings_build.os not in ("Macos",)

    @property
    def _has_ld(self):
        return self.settings_build.os not in ("Macos",)

    def test(self):
        binaries = ["ar", "nm", "objcopy", "objdump", "ranlib", "readelf", "strip"]
        if self._has_as:
            binaries.append("as")
        if self._has_ld:
            binaries.append("ld")

        for binary in binaries:
            self.run(f"{binary} --version", env="conanbuild")

        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
