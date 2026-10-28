import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class LapackReferenceConan(ConanFile):
    name = "lapack-reference"
    description = "LAPACK is a library of Fortran subroutines for solving the most commonly occurring problems in numerical linear algebra"
    license = "BSD-3-Clause-Open-MPI"
    homepage = "https://github.com/Reference-LAPACK/lapack"
    topics = ("linear-algebra", "matrix-factorization", "linear-equations", "svd", "singular-values", "eigenvectors", "eigenvalues")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    @property
    def extension_properties(self):
        return {"fortran_name_mangling": self.fortran.mangling.value}
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_deprecated": [True, False],
        "single": [True, False],
        "double": [True, False],
        "complex": [True, False],
        "complex16": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_deprecated": False,
        "single": True,
        "double": True,
        "complex": True,
        "complex16": True,
    }
    options_description = {
        "build_deprecated": "Build deprecated routines",
        "single": "Build single precision real",
        "double": "Build double precision real",
        "complex": "Build single precision complex",
        "complex16": "Build double precision complex",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("blas/latest", transitive_headers=True, transitive_libs=True)
        self.fortran.requires_runtime()

    def validate(self):
        self.fortran.validate_settings()
        mangling = self.dependencies["blas"].extension_properties["fortran_name_mangling"]
        if mangling != self.fortran.mangling.value:
            raise ConanInvalidConfiguration(
                f"BLAS uses {mangling}, but the configured Fortran toolchain uses {self.fortran.mangling.value}"
            )

    def validate_build(self):
        self.fortran.validate_build()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    @property
    def _is_64bit(self):
        return self.dependencies["blas"].options.interface == "ilp64"

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_DEPRECATED"] = self.options.build_deprecated
        tc.variables["BUILD_SINGLE"] = self.options.single
        tc.variables["BUILD_DOUBLE"] = self.options.double
        tc.variables["BUILD_COMPLEX"] = self.options.complex
        tc.variables["BUILD_COMPLEX16"] = self.options.complex16
        tc.variables["USE_OPTIMIZED_BLAS"] = True
        tc.variables["USE_OPTIMIZED_LAPACK"] = False
        tc.variables["CBLAS"] = False
        tc.variables["LAPACKE"] = True
        tc.variables["BUILD_INDEX64"] = self._is_64bit
        tc.variables["BUILD_INDEX64_EXT_API"] = False
        # VerifyFortranC module in CMake fails to build a test executable otherwise.
        if self.settings.os != "Windows":
            tc.variables["CMAKE_Fortran_FLAGS"] = "-fPIC"
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lapack")
        lib_prefix = "lib" if self.settings.os == "Windows" and not self.options.shared else ""
        lib_suffix = "64" if self._is_64bit else ""

        self.cpp_info.components["lapack"].set_property("cmake_target_name", "lapack")
        self.cpp_info.components["lapack"].set_property("pkg_config_name", "lapack")
        self.cpp_info.components["lapack"].libs = [f"{lib_prefix}lapack{lib_suffix}"]
        self.cpp_info.components["lapack"].requires = ["blas::blas"]
        if self._is_64bit:
            self.cpp_info.components["lapack"].defines.append("LAPACK_ILP64")
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["lapack"].system_libs.append("m")
        self.fortran.add_runtime_to_cpp_info(self.cpp_info.components["lapack"])

        self.cpp_info.components["lapacke"].set_property("cmake_target_name", "lapacke")
        self.cpp_info.components["lapacke"].set_property("pkg_config_name", "lapacke")
        self.cpp_info.components["lapacke"].libs = [f"{lib_prefix}lapacke{lib_suffix}"]
        self.cpp_info.components["lapacke"].requires = ["lapack"]
        if self.settings.os == "Windows":
            self.cpp_info.components["lapacke"].defines.extend(["HAVE_LAPACK_CONFIG_H", "LAPACK_COMPLEX_STRUCTURE"])
