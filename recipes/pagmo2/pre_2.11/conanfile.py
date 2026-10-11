import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class Pagmo2Conan(ConanFile):
    name = "pagmo2"
    description = "pagmo is a C++ scientific library for massively parallel optimization."
    license = "LGPL-3.0-or-later OR GPL-3.0-or-later"
    homepage = "https://esa.github.io/pagmo2"
    topics = ("pagmo", "optimization", "parallel-computing", "genetic-algorithm", "metaheuristics", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_eigen": [True, False],
        "with_nlopt": [True, False],
        "with_ipopt": [True, False],
    }
    default_options = {
        "with_eigen": False,
        "with_nlopt": False,
        "with_ipopt": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.71.0]", transitive_headers=True, libs=False)
        self.requires("onetbb/[>=2021]")
        if self.options.with_eigen:
            self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        if self.options.with_nlopt:
            self.requires("nlopt/2.7.1", transitive_headers=True, transitive_libs=True)

    def package_id(self):
        self.info.settings.clear()

    def validate(self):
        check_min_cppstd(self, 11)
        # TODO: add ipopt support
        if self.options.with_ipopt:
            raise ConanInvalidConfiguration("ipopt recipe not available yet in CCI")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # CMake v4 support
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 3.2)",
                        "cmake_minimum_required(VERSION 3.5)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PAGMO_BUILD_TESTS"] = False
        tc.variables["PAGMO_BUILD_TUTORIALS"] = False
        tc.variables["PAGMO_WITH_EIGEN3"] = self.options.with_eigen
        tc.variables["PAGMO_WITH_NLOPT"] = self.options.with_nlopt
        tc.variables["PAGMO_WITH_IPOPT"] = self.options.with_ipopt
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            pattern="COPYING.*",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "pagmo")
        self.cpp_info.set_property("cmake_target_name", "Pagmo::pagmo")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("pthread")

        self.cpp_info.requires = ["boost::boost", "onetbb::onetbb"]
        if self.options.with_eigen:
            self.cpp_info.requires.append("eigen::eigen")
        if self.options.with_nlopt:
            self.cpp_info.requires.append("nlopt::nlopt")
