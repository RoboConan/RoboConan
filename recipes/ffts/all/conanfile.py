import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class FftsConan(ConanFile):
    name = "ffts"
    description = "FFTS: The Fastest Fourier Transform in the South"
    license = "BSD-3-Clause"
    homepage = "https://github.com/linkotec/ffts"
    topics = ("fft", "fast-fourier-transform", "math", "signal-processing")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "dynamic_code_generation": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "dynamic_code_generation": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.dynamic_code_generation

    def layout(self):
        cmake_layout(self, src_folder="src")

    def build_requirements(self):
        if self.settings.arch in ["x86", "x86_64"]:
            self.tool_requires("nasm/[*]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # CMake v4 support
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 2.8.12 FATAL_ERROR)",
                        "cmake_minimum_required(VERSION 3.10)")
        # Disable tests
        replace_in_file(self, "CMakeLists.txt", "ENABLE_STATIC OR ENABLE_SHARED", "0")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_STATIC"] = not self.options.shared
        tc.cache_variables["ENABLE_SHARED"] = self.options.shared
        tc.cache_variables["GENERATE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.cache_variables["DISABLE_DYNAMIC_CODE"] = not self.options.get_safe("dynamic_code_generation", False)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYRIGHT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "ffts")
        self.cpp_info.libs = ["ffts"]
        self.cpp_info.includedirs = ["include/ffts"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
