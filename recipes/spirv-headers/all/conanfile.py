import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SpirvheadersConan(ConanFile):
    name = "spirv-headers"
    homepage = "https://github.com/KhronosGroup/SPIRV-Headers"
    description = "Header files for the SPIRV instruction set."
    license = "MIT-KhronosGroup"
    topics = ("spirv", "spirv-v", "vulkan", "opengl", "opencl", "khronos")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"namespace": ["ANY"]}
    default_options = {"namespace": "spv"}

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        self.info.settings.clear()

    def validate(self):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(self.options.namespace)):
            raise ConanInvalidConfiguration("namespace must be a C++ identifier")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        assert "VERSION 1.5.5" in load(self, "CMakeLists.txt")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SPIRV_HEADERS_SKIP_EXAMPLES"] = True
        if Version(self.version) > "1.3.275.0":
            tc.variables["SPIRV_HEADERS_ENABLE_TESTS"] = False
        if Version(self.version) < "1.3.250.0":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SPIRV-Headers")
        self.cpp_info.set_property("cmake_target_name", "SPIRV-Headers::SPIRV-Headers")
        self.cpp_info.set_property("pkg_config_name", "SPIRV-Headers")
        # .pc and CMake version has been fixed at 1.5.5 since 1.2.198.0
        self.cpp_info.set_property("system_package_version", "1.5.5")
        if self.options.namespace != "spv":
            self.cpp_info.defines = [f"spv={self.options.namespace}"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
