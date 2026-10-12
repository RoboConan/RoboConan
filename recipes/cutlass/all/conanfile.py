import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class CutlassConan(ConanFile):
    name = "cutlass"
    description = "CUTLASS: CUDA Templates for Linear Algebra Subroutines"
    license = "BSD-3-Clause"
    homepage = "https://github.com/NVIDIA/cutlass"
    topics = ("linear-algebra", "gpu", "cuda", "deep-learning", "nvidia", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "install_examples_headers": [True, False],
    }
    default_options = {
        "install_examples_headers": False,
    }
    no_copy_source = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        self.info.settings.clear()
        self.info.conf.clear()

    def validate(self):
        check_min_cppstd(self, 17 if Version(self.version) >= "3.0" else 11)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.19 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Don't look for CUDA when only installing headers
        save(self, os.path.join(self.source_folder, "CUDA.cmake"), "")

    def generate(self):
        # Install via CMake to ensure headers are configured correctly
        tc = CMakeToolchain(self)
        tc.cache_variables["CUTLASS_ENABLE_HEADERS_ONLY"] = True  # non-header-only is only used for tests, tools and examples
        tc.cache_variables["CUTLASS_ENABLE_LIBRARY"] = True
        tc.cache_variables["CUTLASS_ENABLE_TOOLS"] = False
        tc.cache_variables["CUTLASS_ENABLE_CUBLAS"] = False  # used only in tests
        tc.cache_variables["CUTLASS_ENABLE_CUDNN"] = False  # used only in tests
        tc.cache_variables["CUTLASS_ENABLE_PROFILER"] = False  # tool
        tc.cache_variables["CUTLASS_ENABLE_PERFORMANCE"] = False  # tool
        tc.cache_variables["CUTLASS_ENABLE_TESTS"] = False
        tc.cache_variables["CUTLASS_INSTALL_TESTS"] = False
        tc.cache_variables["CMAKE_SUPPRESS_REGENERATION"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.install_examples_headers:
            for pattern in ["*.h", "*.hpp", "*.cuh"]:
                copy(self, pattern,
                     os.path.join(self.source_folder, "examples"),
                     os.path.join(self.package_folder, "include", "cutlass", "examples"))
        # Install tools headers even if CUTLASS_ENABLE_TOOLS is disabled
        copy(self, "*", os.path.join(self.source_folder, "tools", "util", "include"), os.path.join(self.package_folder, "include"))
        rmdir(self, os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "test"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "NvidiaCutlass")
        self.cpp_info.set_property("cmake_target_name", "nvidia::cutlass::cutlass")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.options.install_examples_headers:
            self.cpp_info.includedirs.append(os.path.join("include", "cutlass", "examples"))
