import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class SuiteSparseCholmodConan(ConanFile):
    name = "suitesparse-cholmod"
    description = "CHOLMOD: Routines for factorizing sparse symmetric positive definite matrices in SuiteSparse"
    license = "LGPL-2.1-or-later AND Apache-2.0"
    homepage = "https://people.engr.tamu.edu/davis/suitesparse.html"
    topics = ("mathematics", "sparse-matrix", "linear-algebra", "matrix-factorization")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cuda": [True, False],
        "build_matrixops": [True, False],
        "build_modify": [True, False],
        "build_partition": [True, False],
        "build_supernodal": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cuda": False,
        "build_matrixops": False,
        "build_modify": False,
        "build_partition": True,
        "build_supernodal": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _license_is_gpl(self):
        return self.options.cuda or self.options.build_matrixops or self.options.build_modify or self.options.build_supernodal

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self._license_is_gpl:
            self.license = "LGPL-2.1-or-later AND GPL-2.0-or-later AND Apache-2.0"
        if not self.options.cuda:
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # BLAS and OpenMP are provided via suitesparse-config
        self.requires("suitesparse-config/[^7.8.3]", transitive_headers=True, transitive_libs=True)
        self.requires("suitesparse-amd/[^3.3.3]")
        self.requires("suitesparse-camd/[^3.3.3]")
        self.requires("suitesparse-colamd/[^3.3.4]")
        self.requires("suitesparse-ccolamd/[^3.3.4]")

        # A modified vendored version of METIS v5.1.0 is included,
        # but it has been modified to not conflict with the general version

        if self.options.cuda:
            self.cuda.requires("cudart", transitive_headers=True)
            self.cuda.requires("cublas", transitive_headers=True)
            self.cuda.requires("nvrtc")

    def validate(self):
        if self.options.cuda:
            self.cuda.validate_settings()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")
        if self.options.cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Don't force a static cudart
        replace_in_file(self, "CHOLMOD/CMakeLists.txt", "CUDA_RUNTIME_LIBRARY Static", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["CHOLMOD_GPL"] = self._license_is_gpl
        tc.variables["CHOLMOD_MATRIXOPS"] = self.options.build_matrixops
        tc.variables["CHOLMOD_MODIFY"] = self.options.build_modify
        tc.variables["CHOLMOD_PARTITION"] = self.options.build_partition
        tc.variables["CHOLMOD_SUPERNODAL"] = self.options.build_supernodal
        tc.variables["SUITESPARSE_USE_OPENMP"] = True
        tc.variables["SUITESPARSE_USE_CUDA"] = self.options.cuda
        tc.variables["SUITESPARSE_DEMOS"] = False
        tc.variables["SUITESPARSE_USE_FORTRAN"] = False  # Fortran sources are translated to C instead
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)  # for BLAS try_compile()-s
        if self.options.cuda:
            tc.variables["CMAKE_CUDA_ARCHITECTURES"] = str(self.settings.cuda.architectures).replace(",", ";")
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        if self.options.cuda:
            tc = self.cuda.CudaToolchain()
            tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="CHOLMOD")
        cmake.build()

    def package(self):
        copy(self, "License.txt", os.path.join(self.source_folder, "CHOLMOD", "Doc"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CHOLMOD")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::CHOLMOD")
        if not self.options.shared:
            self.cpp_info.set_property("cmake_target_aliases", ["SuiteSparse::CHOLMOD_static"])
        self.cpp_info.set_property("pkg_config_name", "CHOLMOD")

        suffix = "_static" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.libs = ["cholmod" + suffix]
        self.cpp_info.includedirs.append("include/suitesparse")
        self.cpp_info.requires = [
            "suitesparse-config::suitesparse-config",
            "suitesparse-amd::suitesparse-amd",
            "suitesparse-camd::suitesparse-camd",
            "suitesparse-colamd::suitesparse-colamd",
            "suitesparse-ccolamd::suitesparse-ccolamd",
        ]

        if self.options.cuda:
            self.cpp_info.defines.append("CHOLMOD_HAS_CUDA")
            self.cpp_info.requires.extend([
                "cudart::cudart_",
                "cublas::cublas_",
                "nvrtc::nvrtc",
            ])

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")

        if not self._license_is_gpl:
            self.cpp_info.defines.append("NGPL")
