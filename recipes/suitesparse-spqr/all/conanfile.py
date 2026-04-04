import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class SuiteSparseSpqrConan(ConanFile):
    name = "suitesparse-spqr"
    description = "SPQR: Multithreaded, multifrontal, rank-revealing sparse QR factorization method in SuiteSparse"
    license = "GPL-2.0-or-later"
    homepage = "https://people.engr.tamu.edu/davis/suitesparse.html"
    topics = ("mathematics", "sparse-matrix", "linear-algebra", "matrix-factorization", "qr-factorization")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cuda": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cuda": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["suitesparse-cholmod"].build_supernodal = True
        self.options["suitesparse-cholmod"].build_matrixops = True
        if self.options.cuda:
            self.options["suitesparse-cholmod"].cuda = True
        else:
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # BLAS and OpenMP are provided via suitesparse-config
        self.requires("suitesparse-config/[^7.8.3]", transitive_headers=True, transitive_libs=True)
        self.requires("suitesparse-cholmod/[^5.3.0]", transitive_headers=True, transitive_libs=True)

        if self.options.cuda:
            self.cuda.requires("cudart", transitive_headers=True)
            self.cuda.requires("cublas", transitive_headers=True)
            self.cuda.requires("nvrtc")

    def validate(self):
        if self.options.cuda:
            if not self.dependencies["suitesparse-cholmod"].options.cuda:
                raise ConanInvalidConfiguration("suitesparse-spqr/*:cuda=True option requires suitesparse-cholmod/*:cuda=True")
            self.cuda.validate_settings()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")
        if self.options.cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Don't force a static cudart
        replace_in_file(self, "SPQR/GPURuntime/CMakeLists.txt", "CUDA_RUNTIME_LIBRARY Static", "")
        replace_in_file(self, "SPQR/GPUQREngine/CMakeLists.txt", "CUDA_RUNTIME_LIBRARY Static", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_VERBOSE_MAKEFILE"] = True
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["SUITESPARSE_USE_OPENMP"] = True
        tc.variables["SUITESPARSE_USE_CUDA"] = self.options.cuda
        tc.variables["SPQR_USE_CUDA"] = self.options.cuda
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
        cmake.configure(build_script_folder="SPQR")
        cmake.build()

    def package(self):
        copy(self, "License.txt", os.path.join(self.source_folder, "SPQR", "Doc"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SPQR")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::SPQR")
        if not self.options.shared:
            self.cpp_info.set_property("cmake_target_aliases", ["SuiteSparse::SPQR_static"])
        self.cpp_info.set_property("pkg_config_name", "SPQR")

        suffix = "_static" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.libs = ["spqr" + suffix]
        self.cpp_info.includedirs.append("include/suitesparse")
        self.cpp_info.requires = [
            "suitesparse-config::suitesparse-config",
            "suitesparse-cholmod::suitesparse-cholmod",
        ]

        if self.options.cuda:
            self.cpp_info.defines.append("SPQR_HAS_CUDA")
            self.cpp_info.requires.extend([
                "cudart::cudart_",
                "cublas::cublas_",
                "nvrtc::nvrtc",
            ])

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
