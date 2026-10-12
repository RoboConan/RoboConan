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
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")

        self.run("protoc --version", env="conanbuild")
        # Invoke protoc in the same way CMake would
        self.run(f"protoc --proto_path={self.source_folder} --cpp_out={self.build_folder} {self.source_folder}/addressbook.proto", env="conanbuild")
        assert os.path.exists(os.path.join(self.build_folder,"addressbook.pb.cc"))
        assert os.path.exists(os.path.join(self.build_folder,"addressbook.pb.h"))
