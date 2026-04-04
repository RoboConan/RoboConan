import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.files.files import replace_in_file
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class SuiteSparseSpexConan(ConanFile):
    name = "suitesparse-spex"
    description = "SPEX: Software package for SParse EXact algebra in SuiteSparse"
    license = "GPL-2.0-or-later OR LGPL-3.0-or-later"
    homepage = "https://people.engr.tamu.edu/davis/suitesparse.html"
    topics = ("mathematics", "sparse-matrix", "linear-algebra", "exact-linear-algebra")

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
        self.requires("suitesparse-amd/[^3.3.3]")
        self.requires("suitesparse-colamd/[^3.3.4]")
        # https://github.com/DrTimothyAldenDavis/SuiteSparse/blob/v7.7.0/SPEX/Include/SPEX.h#L96-L97
        self.requires("gmp/[^6.3.0]", transitive_headers=True, transitive_libs=True)
        self.requires("mpfr/[^4.2.1]", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["SUITESPARSE_USE_OPENMP"] = True
        tc.variables["SUITESPARSE_USE_CUDA"] = False
        tc.variables["SUITESPARSE_DEMOS"] = False
        tc.variables["SUITESPARSE_USE_FORTRAN"] = False  # Fortran sources are translated to C instead
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("gmp", "cmake_file_name", "GMP")
        deps.set_property("mpfr", "cmake_file_name", "MPFR")
        deps.generate()

    def _patch_sources(self):
        # Disable MATLAB wrapper generation, which otherwise fails with
        # "get_filename_component called with incorrect number of arguments"
        replace_in_file(self, os.path.join(self.source_folder, "SPEX", "CMakeLists.txt"),
                        "if ( BUILD_SHARED_LIBS AND NOT SUITESPARSE_ROOT_CMAKELISTS )",
                        "if ( FALSE )")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder="SPEX")
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", os.path.join(self.source_folder, "SPEX"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SPEX")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::SPEX")
        if not self.options.shared:
            self.cpp_info.set_property("cmake_target_aliases", ["SuiteSparse::COLAMD_static"])
        self.cpp_info.set_property("pkg_config_name", "SPEX")

        suffix = "_static" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.libs = ["spex" + suffix]
        self.cpp_info.includedirs.append("include/suitesparse")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
