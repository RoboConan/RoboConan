import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, cmake_layout, CMakeToolchain
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class EigenConan(ConanFile):
    name = "eigen"
    description = ("Eigen is a C++ template library for linear algebra: matrices, vectors,"
                   " numerical solvers, and related algorithms.")
    license = "MPL-2.0 AND BSD-3-Clause AND Minpack AND Apache-2.0"
    topics = ("algebra", "linear-algebra", "matrix", "vector", "numerical", "header-only")
    homepage = "http://eigen.tuxfamily.org"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_openmp": [True, False],
        "MPL2_only": [True, False],
    }
    default_options = {
        "with_openmp": True,
        # No longer applicable in Eigen 5.x.
        # As of Eigen 3.4.0, only the following were LGPL:
        #   Eigen/src/SparseCholesky/SimplicialCholesky.h
        #   Eigen/src/OrderingMethods/Amd.h
        #   unsupported/Eigen/src/IterativeSolvers/*
        "MPL2_only": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if Version(self.version) < "5.0":
            # Based on https://salsa.debian.org/science-team/eigen3/-/blob/debian/3.4.0-5/debian/copyright
            if self.options.MPL2_only:
                self.license = "MPL-2.0 AND BSD-3-Clause"
            else:
                self.license = "MPL-2.0 AND BSD-3-Clause AND LGPL-2.1-or-later"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if Version(self.version) >= "5.0":
            check_min_cppstd(self, "14")
        else:
            check_min_cppstd(self, "03")

    def requirements(self):
        if self.options.with_openmp:
            self.requires("openmp/system")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        if Version(self.version) < "3.4.0":
            replace_in_file(self, "CMakeLists.txt",
                            "cmake_minimum_required(VERSION 2.8.5)",
                            "cmake_minimum_required(VERSION 3.5)")
        if Version(self.version) <= "3.4.0":
            self.output.info("Patching DisableStupidWarnings.h to the latest version to avoid warnings from newer compiler versions")
            path = "Eigen/src/Core/util/DisableStupidWarnings.h"
            assert os.path.isfile(path)
            download(self, **self.conan_data["disable_stupid_warnings_h"][0], filename=path)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["EIGEN_BUILD_BLAS"] = False  # only used in tests and benchmarks
        tc.cache_variables["EIGEN_BUILD_LAPACK"] = False
        tc.cache_variables["BUILD_TESTING"] = not self.conf.get("tools.build:skip_test", default=True, check_type=bool)
        tc.cache_variables["EIGEN_TEST_NOQT"] = True
        tc.cache_variables["EIGEN_BUILD_DOC"] = False
        tc.cache_variables["EIGEN_BUILD_DEMOS"] = False
        tc.cache_variables["EIGEN_BUILD_PKGCONFIG"] = False
        tc.cache_variables["EIGEN_BUILD_CMAKE_PACKAGE"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING.*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Eigen3")
        self.cpp_info.set_property("cmake_target_name", "Eigen3::Eigen")
        self.cpp_info.set_property("pkg_config_name", "eigen3")
        self.cpp_info.includedirs = ["include/eigen3"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
        if self.options.get_safe("MPL2_only"):
            self.cpp_info.defines = ["EIGEN_MPL2_ONLY"]
        if not self.options.with_openmp:
            self.cpp_info.defines.append("EIGEN_DONT_PARALLELIZE")
