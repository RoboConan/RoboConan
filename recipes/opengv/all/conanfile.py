import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import *

required_conan_version = ">=2.1"


class opengvConan(ConanFile):
    name = "opengv"
    description = "A collection of computer vision methods for solving geometric vision problems"
    homepage = "https://github.com/laurentkneip/opengv"
    license = "BSD-3-Clause"
    topics = ("computer-vision", "geometric", "pose", "triangulation", "point-cloud")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_python_bindings": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_python_bindings": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        if self.options.with_python_bindings:
            self.requires("pybind11/[^2.10.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 3.1.3)",
                        "cmake_minimum_required(VERSION 3.5)")
        replace_in_file(self, "CMakeLists.txt", "CXX_STANDARD 11", "")
        replace_in_file(self, "CMakeLists.txt", "DEBUG_POSTFIX d", "")
        replace_in_file(self, "include/opengv/types.hpp", "#include <stdlib.h>", "#include <cassert>\n#include <cstdlib>")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["BUILD_PYTHON"] = self.options.with_python_bindings
        tc.cache_variables["BUILD_POSITION_INDEPENDENT_CODE"] = False  # Handled automatically by Conan/CMake
        if self.settings.compiler == "msvc":
            # Apply some fixes from https://github.com/laurentkneip/opengv/pull/126
            # Disable Eigen half-precision float to avoid MSVC ostream operator conflict
            tc.preprocessor_definitions["EIGEN_HAS_HALF_FLOAT"] = "0"
            # Increase stack size for large Groebner matrix allocations in fivept_kneip and sixpt algorithms
            tc.extra_exelinkflags.append("/STACK:8388608")
        tc.generate()

        cd = CMakeDeps(self)
        cd.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "License.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "opengv")
        self.cpp_info.set_property("cmake_target_name", "opengv")
        self.cpp_info.libs = ["opengv"]
        if self.options.with_python_bindings:
            opengv_dist_packages = os.path.join(self.package_folder, "lib", "python3", "dist-packages")
            self.runenv_info.prepend_path("PYTHONPATH", opengv_dist_packages)
