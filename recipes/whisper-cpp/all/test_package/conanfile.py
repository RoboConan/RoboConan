import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("pkgconf/[<4]")

    def layout(self):
        cmake_layout(self)

    def build(self):
        self.run(
            f"pkgconf --with-path={self.generators_folder} --validate whisper parakeet",
            env="conanbuild",
        )
        self.run(
            f"pkgconf --with-path={self.generators_folder} --cflags --libs whisper parakeet",
            env="conanbuild",
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
