import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class SuiteSparseCxsparseConan(ConanFile):
    name = "suitesparse-cxsparse"
    description = "CXSparse: Software package for permuting a matrix into block upper triangular form in SuiteSparse"
    license = "LGPL-2.1-or-later"
    homepage = "https://people.engr.tamu.edu/davis/suitesparse.html"
    topics = ("mathematics", "sparse-matrix", "linear-algebra", "matrix-permutation")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # BLAS and OpenMP are provided via suitesparse-config
        self.requires("suitesparse-config/[^7.8.3]", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _complex_supported(self):
        if is_msvc(self):
            # ANSI C complex data type is not supported by MSVC
            return False
        if self.settings.os == "Android":
            # creal, cimag and other complex-valued math functions are only available since API level 23
            return int(self.settings.os.api_level.value) >= 23
        return True

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["SUITESPARSE_USE_OPENMP"] = True
        tc.variables["SUITESPARSE_USE_CUDA"] = False
        tc.variables["SUITESPARSE_DEMOS"] = False
        tc.variables["SUITESPARSE_USE_FORTRAN"] = False  # Fortran sources are translated to C instead
        tc.variables["CXSPARSE_USE_COMPLEX"] = self._complex_supported
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="CXSparse")
        cmake.build()

    def package(self):
        copy(self, "License.txt", os.path.join(self.source_folder, "CXSparse", "Doc"), os.path.join(self.package_folder, "licenses"))
        copy(self, "lesser.txt", os.path.join(self.source_folder, "CXSparse", "Doc"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CXSparse")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::CXSparse")
        if not self.options.shared:
            self.cpp_info.set_property("cmake_target_aliases", ["SuiteSparse::CXSparse_static"])
        self.cpp_info.set_property("pkg_config_name", "CXSparse")

        suffix = "_static" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.libs = ["cxsparse" + suffix]
        self.cpp_info.includedirs.append("include/suitesparse")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")

        if not self._complex_supported:
            self.cpp_info.defines.append("NCOMPLEX")
