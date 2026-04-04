import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.21"  # for cmake_extra_variables


class SuiteSparseConfigConan(ConanFile):
    name = "suitesparse-config"
    description = "Configuration for SuiteSparse libraries"
    license = "BSD-3-Clause"
    homepage = "https://people.engr.tamu.edu/davis/suitesparse.html"
    topics = ("mathematics", "sparse-matrix", "linear-algebra")

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
        self.requires("lapack/latest", transitive_headers=True, transitive_libs=True)
        self.requires("openmp/system", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _bla_vendor(self):
        return {
            "openblas": "OpenBLAS",
            "mkl": "Intel10",
            "blis": "FLAME",
            "accelerate": "Apple",
            "armpl": "Arm",
            "nvpl": "NVPL",
        }.get(str(self.dependencies["blas"].options.provider), "Generic")

    @property
    def _blas_variables(self):
        blas_variables = {}
        blas_variables["BLA_VENDOR"] = self._bla_vendor
        blas_variables["SUITESPARSE_USE_64BIT_BLAS"] = self.dependencies["blas"].options.interface == "ilp64"
        # Skip try_run()-s
        if self._bla_vendor == "OpenBLAS":
            blas_variables["OPENBLAS_2015_COMPILES"] = True
            blas_variables["OPENBLAS_2015_RUNS"] = True
            is_new = bool(Version(self.dependencies["openblas"].ref.version) >= "0.3.27")
            blas_variables["OPENBLAS_2024_COMPILES"] = is_new
            blas_variables["OPENBLAS_2024_RUNS"] = is_new
        elif self._bla_vendor == "Intel10":
            blas_variables["MKL_COMPILES"] = True
            blas_variables["MKL_RUNS"] = True
        return blas_variables


    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["SUITESPARSE_USE_OPENMP"] = True
        tc.cache_variables["SUITESPARSE_USE_CUDA"] = False
        tc.cache_variables["SUITESPARSE_DEMOS"] = False
        tc.cache_variables["SUITESPARSE_USE_STRICT"] = True  # don't allow implicit dependencies
        tc.cache_variables["SUITESPARSE_USE_FORTRAN"] = False  # Fortran sources are translated to C instead
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)  # for BLAS try_compile()-s
        tc.cache_variables.update(self._blas_variables)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="SuiteSparse_config")
        cmake.build()

    def _copy_license(self):
        # Extract the license applicable to SuiteSparse_config from all licenses in SuiteSparse
        full_license_info = load(self, os.path.join(self.source_folder, "LICENSE.txt"))
        bsd3 = re.search(r"==> Example License <==\n\n(.+?)\n==> ParU License <==", full_license_info, re.DOTALL).group(1)
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE.txt"), bsd3)

    def package(self):
        self._copy_license()
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SuiteSparse_config")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::SuiteSparseConfig")
        if not self.options.shared:
            self.cpp_info.set_property("cmake_target_aliases", ["SuiteSparse::SuiteSparseConfig_static"])
        self.cpp_info.set_property("pkg_config_name", "SuiteSparse_config")

        suffix = "_static" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.libs = ["suitesparseconfig" + suffix]
        self.cpp_info.includedirs.append("include/suitesparse")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")

        # All available BLAS implementations currently available under blas/latest use a single underscore suffix
        self.cpp_info.defines.append("BLAS64_SUFFIX=_")

        self.cpp_info.set_property("cmake_extra_variables", self._blas_variables)
