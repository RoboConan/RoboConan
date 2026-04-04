import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class ProxSuiteConan(ConanFile):
    name = "proxsuite"
    description = ("ProxSuite is a collection of open-source, numerically robust, precise, "
                   "and efficient numerical solvers (e.g., LPs, QPs, etc.) rooted in revisited primal-dual proximal algorithms. ")
    license = "BSD-2-Clause"
    homepage = "https://github.com/Simple-Robotics/proxsuite"
    topics = ("optimization", "linear-programming", "quadratic-programming", "robotics", "proximal-algorithms", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "vectorization": [True, False],
        "openmp": [True, False],
    }
    default_options = {
        "vectorization": True,
        "openmp": True,
    }

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        if self.options.vectorization:
            self.requires("simde/[>=0.8 <1]", transitive_headers=True)
        if self.options.openmp:
            self.requires("openmp/system")

    def validate(self):
        check_min_cppstd(self, 14)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22]")
        self.tool_requires("jrl-cmakemodules/[*]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 3.10)",
                        "cmake_minimum_required(VERSION 3.22)")
        # get jrl-cmakemodules from Conan
        replace_in_file(self, "CMakeLists.txt", "set(JRL_CMAKE_MODULES ", " # set(JRL_CMAKE_MODULES ")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_BENCHMARK"] = False
        tc.cache_variables["BUILD_DOCUMENTATION"] = False
        tc.cache_variables["INSTALL_DOCUMENTATION"] = False
        tc.cache_variables["BUILD_PYTHON_INTERFACE"] = False
        tc.cache_variables["TEST_JULIA_INTERFACE"] = False
        tc.cache_variables["BUILD_WITH_VECTORIZATION_SUPPORT"] = self.options.vectorization
        tc.cache_variables["BUILD_WITH_OPENMP_SUPPORT"] = self.options.openmp
        tc.cache_variables["JRL_CMAKE_MODULES"] = self.dependencies.build["jrl-cmakemodules"].cpp_info.builddirs[0].replace("\\", "/")
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "proxsuite")
        self.cpp_info.set_property("cmake_target_name", "proxsuite::proxsuite")
        self.cpp_info.set_property("pkg_config_name", "proxsuite")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.options.vectorization:
            self.cpp_info.set_property("cmake_target_aliases", ["proxsuite::proxsuite-vectorized"])
            self.cpp_info.defines.append("PROXSUITE_VECTORIZE")

        if self.settings.os == "Windows":
            self.cpp_info.defines.append("NOMINMAX")
            if self.settings.compiler == "msvc":
                self.cpp_info.cxxflags.extend(["/permissive-", "/bigobj"])
