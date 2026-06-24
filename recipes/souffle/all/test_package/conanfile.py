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

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def build(self):
        self.run("souffle --version", env="conanbuild")
        dl_path = os.path.join(self.source_folder, "hello.dl")
        cpp_path = os.path.join(self.build_folder, "hello.cpp")
        # --no-preprocessor: hello.dl has no preprocessor directives, and the
        # default C preprocessor (gcc -E) is host-environment dependent.
        # Use --preprocessor to set the correct executable when using downstream.
        self.run(f"souffle --no-preprocessor -g {cpp_path} {dl_path}", env="conanbuild")
        assert os.path.exists(cpp_path)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
