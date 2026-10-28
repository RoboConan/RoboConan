import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        src_path = os.path.join(self.source_folder, "hello.c")
        bin_path = os.path.join(self.cpp.build.bindir, "test_package_c")
        self.run(f"icx '{src_path}' -o '{bin_path}'")
        if can_run(self):
            self.run(bin_path, env="conanrun")

        src_path = os.path.join(self.source_folder, "hello.cpp")
        bin_path = os.path.join(self.cpp.build.bindir, "test_package_cpp")
        self.run(f"icpx '{src_path}' -o '{bin_path}'")
        if can_run(self):
            self.run(bin_path, env="conanrun")

        src_path = os.path.join(self.source_folder, "hello_sycl.cpp")
        bin_path = os.path.join(self.cpp.build.bindir, "test_package_sycl")
        self.run(f"icpx -fsycl '{src_path}' -o '{bin_path}'")
