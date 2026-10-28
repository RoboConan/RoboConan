import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class QpDunesConan(ConanFile):
    name = "qpdunes"
    description = "qpDUNES: An Implementation of the Online Active Set Strategy for fast Model Predictive Control"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/acados/qpDUNES-dev"
    topics = ("optimization", "quadratic-programming", "mpc", "control")
    provies = "qpoases"  # vendored
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": False,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        if self.options.with_openmp:
            self.requires("openmp/system")

    def validate(self):
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        if mangling != "lower_underscore":
            raise ConanInvalidConfiguration("qpDUNES requires LAPACK with lower_underscore names")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt",
                        "CMAKE_MINIMUM_REQUIRED( VERSION 2.8 )",
                        "CMAKE_MINIMUM_REQUIRED( VERSION 3.5 )")
        replace_in_file(self, "CMakeLists.txt",
                        "FIND_PACKAGE( OpenMP )",
                        "FIND_PACKAGE( OpenMP REQUIRED )")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["QPDUNES_WITH_BLAS"] = True
        tc.cache_variables["QPDUNES_WITH_LAPACK"] = True
        tc.cache_variables["QPDUNES_PARALLEL"] = self.options.with_openmp
        tc.cache_variables["QPDUNES_ACADOS"] = True  # This disables examples
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["qpdunes"]
        self.cpp_info.includedirs.append("include/qpdunes")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
        if not self.options.shared and stdcpp_library(self):
            self.cpp_info.system_libs.append(stdcpp_library(self))
