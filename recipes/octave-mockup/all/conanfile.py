import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class OctaveMockupConan(ConanFile):
    name = "octave-mockup"
    description = "Mockup interface for Octave"
    license = "MIT"
    homepage = "https://github.com/casadi/mockups"
    topics = ("octave", "mockup", "casadi")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # The mockup declares its own bool type, which is not valid in C23.
        tc.cache_variables["CMAKE_C_STANDARD"] = 17
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="octave")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "cmake"))

    def package_info(self):
            self.cpp_info.set_property("cmake_file_name", "octave")
            self.cpp_info.set_property("cmake_target_name", "octave::octave")

            self.cpp_info.components["octinterp_adaptor"].set_property("cmake_target_name", "octave::octinterp_adaptor")
            self.cpp_info.components["octinterp_adaptor"].libs = ["octinterp_adaptor"]
