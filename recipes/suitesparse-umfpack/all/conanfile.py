import os
from multiprocessing.util import sub_debug

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class SuiteSparseUmfpackConan(ConanFile):
    name = "suitesparse-umfpack"
    description = "UMFPACK: Routines solving sparse linear systems via LU factorization in SuiteSparse"
    license = "GPL-2.0-or-later"
    homepage = "https://people.engr.tamu.edu/davis/suitesparse.html"
    topics = ("mathematics", "sparse-matrix", "linear-algebra", "linear-system-solver", "lu-factorization")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_cholmod": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_cholmod": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # BLAS and OpenMP are provided via suitesparse-config
        self.requires("suitesparse-config/[^7.8.3]", transitive_headers=True, transitive_libs=True)
        self.requires("suitesparse-amd/[^3.3.3]", transitive_headers=True, transitive_libs=True)
        if self.options.with_cholmod:
            self.requires("suitesparse-cholmod/[^5.3.0]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["UMFPACK_USE_CHOLMOD"] = self.options.with_cholmod
        tc.variables["SUITESPARSE_USE_OPENMP"] = True
        tc.variables["SUITESPARSE_USE_CUDA"] = False
        tc.variables["SUITESPARSE_DEMOS"] = False
        tc.variables["SUITESPARSE_USE_FORTRAN"] = False  # Fortran sources are translated to C instead
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)  # for BLAS try_compile()-s
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="UMFPACK")
        cmake.build()

    def package(self):
        copy(self, "License.txt", os.path.join(self.source_folder, "UMFPACK", "Doc"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "UMFPACK")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::UMFPACK")
        if not self.options.shared:
            self.cpp_info.set_property("cmake_target_aliases", ["SuiteSparse::UMFPACK_static"])
        self.cpp_info.set_property("pkg_config_name", "UMFPACK")

        suffix = "_static" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.libs = ["umfpack" + suffix]
        self.cpp_info.includedirs.append("include/suitesparse")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
