import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class OneMathConan(ConanFile):
    name = "onemath"
    description = (
        "The oneAPI Math Library (oneMath) defines a set of fundamental mathematical routines "
        "for use in high-performance computing and other applications. "
        "As part of oneAPI, oneMath is designed to allow execution on a wide variety of computational devices: "
        "CPUs, GPUs, FPGAs, and other accelerators."
    )
    license = "Apache-2.0"
    homepage = "https://github.com/uxlfoundation/oneMath"
    topics = ("math", "numerical", "linear-algebra", "oneapi", "hpc", "blas")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],

        "mklcpu": [True, False],
        "mklgpu": [True, False],
        "armpl": [True, False],
        "netlib_blas": [True, False],
        "generic_sycl_blas": [True, False],
        "portfft": [True, False],
        "cublas": [True, False],
        "curand": [True, False],
        "cusolver": [True, False],
        "cufft": [True, False],
        "cusparse": [True, False],

        "generic_sycl_blas_tune": [None, "intel_cpu", "intel_gpu", "amd_gpu", "nvidia_gpu"],
        "cuda_targets": [None, "ANY"],  # only applied to generic_sycl_blas
        "hip_targets": [None, "ANY"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,

        "mklcpu": True,
        "mklgpu": True,
        "armpl": False,
        "netlib_blas": False,
        "generic_sycl_blas": False,
        "portfft": False,
        "cublas": False,
        "curand": False,
        "cusolver": False,
        "cufft": False,
        "cusparse": False,

        "generic_sycl_blas_tune": None,
        "cuda_targets": None,
        "hip_targets": None,

        "onemkl/*:sycl": True,
        "onemkl/*:threading": "tbb",
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _all_backends(self):
        return ["mklcpu", "mklgpu", "armpl", "netlib_blas", "generic_sycl_blas", "cublas", "curand", "cusolver", "cufft", "cusparse", "portfft"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.generic_sycl_blas:
            self.options.rm_safe("generic_sycl_blas_tune")
            self.options.rm_safe("cuda_targets")
        if not any(self.options.get_safe(x) for x in ["cublas", "curand", "cusolver", "cufft", "cusparse"]):
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"intel-dpcpp-sycl/[~{self.settings.compiler.version}]")

        if self.options.mklcpu or self.options.mklgpu:
            self.requires("onemkl/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.armpl:
            self.requires("armpl/[^25.7]")
        if self.options.netlib_blas:
            self.requires("blas/latest")
        if self.options.portfft:
            self.requires("portfft/[*]")

        if self.options.cublas:
            self.cuda.requires("cublas")
        if self.options.curand:
            self.cuda.requires("curand")
        if self.options.cusolver:
            self.cuda.requires("cusolver")
        if self.options.cufft:
            self.cuda.requires("cufft")
        if self.options.cusparse:
            self.cuda.requires("cusparse")

    def validate(self):
        if self.settings.compiler != "intel-cc" or self.settings.compiler.mode not in ["icx", "dpcpp"]:
            raise ConanInvalidConfiguration("Only Intel icpx and dpcpp compilers are supported")
        if self.options.generic_sycl_blas and any(self.options.get_safe(backend) for backend in
                                                  ["mklcpu", "mklgpu", "armpl", "netlib_blas", "cublas"]):
            raise ConanInvalidConfiguration("Other BLAS backends cannot be enabled if generic_blas is used.")
        if self.options.portfft and any(self.options.get_safe(backend) for backend in
                                        ["mklcpu", "mklgpu", "armpl", "cufft"]):
            raise ConanInvalidConfiguration("Other DFT backends cannot be enabled if portfft is used.")
        if self.options.mklcpu and self.dependencies["onemkl"].options.threading not in ["tbb", "sequential"]:
            raise ConanInvalidConfiguration("The oneMath MKL CPU backend requires oneMKL threading=tbb or sequential")
        if self.options.armpl:
            if self.settings.os not in ["Linux", "FreeBSD"] or self.settings.arch != "armv8":
                raise ConanInvalidConfiguration("The ArmPL backend requires an Arm64 Unix target")
            if self.dependencies["armpl"].options.interface != "ilp64":
                raise ConanInvalidConfiguration("The oneMath ArmPL backend requires armpl:interface=ilp64")
        if not any(self.options.get_safe(backend, False) for backend in self._all_backends):
            raise ConanInvalidConfiguration("At least one backend must be enabled. "
                                            "Please enable at least one of: " + ", ".join(self._all_backends))

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.17]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Move project() to the start of CMakeLists.txt
        replace_in_file(self, "CMakeLists.txt", "project(", "# project(")
        minimum_requires = "cmake_minimum_required (VERSION 3.13)"
        replace_in_file(self, "CMakeLists.txt", minimum_requires, minimum_requires
                        + f"\nproject(oneMath VERSION {self.version} LANGUAGES CXX)")

    def generate(self):
        tc = CMakeToolchain(self)
        # backends
        tc.cache_variables["ENABLE_MKLCPU_BACKEND"] = self.options.mklcpu
        tc.cache_variables["ENABLE_MKLGPU_BACKEND"] = self.options.mklgpu
        tc.cache_variables["ENABLE_MKLCPU_THREAD_TBB"] = self.options.mklcpu and self.dependencies["onemkl"].options.threading == "tbb"
        tc.cache_variables["ENABLE_ARMPL_BACKEND"] = self.options.armpl
        tc.cache_variables["ENABLE_ARMPL_OMP"] = self.options.armpl and self.dependencies["armpl"].options.threading == "omp"
        tc.cache_variables["ENABLE_ARMPL_OPENRNG"] = False
        # blas
        tc.cache_variables["ENABLE_CUBLAS_BACKEND"] = self.options.cublas
        tc.cache_variables["ENABLE_ROCBLAS_BACKEND"] = False
        tc.cache_variables["ENABLE_NETLIB_BACKEND"] = self.options.netlib_blas
        tc.cache_variables["ENABLE_GENERIC_BLAS_BACKEND"] = self.options.generic_sycl_blas
        if self.options.get_safe("generic_sycl_blas_tune"):
            tc.cache_variables["GENERIC_BLAS_TUNING_TARGET"] = self.options.generic_sycl_blas_tune.value.upper()
        # rand
        tc.cache_variables["ENABLE_CURAND_BACKEND"] = self.options.curand
        tc.cache_variables["ENABLE_ROCRAND_BACKEND"] = False
        # lapack
        tc.cache_variables["ENABLE_CUSOLVER_BACKEND"] = self.options.cusolver
        tc.cache_variables["ENABLE_ROCSOLVER_BACKEND"] = False
        # dft
        tc.cache_variables["ENABLE_CUFFT_BACKEND"] = self.options.cufft
        tc.cache_variables["ENABLE_ROCFFT_BACKEND"] = False
        tc.cache_variables["ENABLE_PORTFFT_BACKEND"] = self.options.portfft
        # sparse
        tc.cache_variables["ENABLE_CUSPARSE_BACKEND"] = self.options.cusparse
        tc.cache_variables["ENABLE_ROCSPARSE_BACKEND"] = False

        tc.cache_variables["ONEMATH_SYCL_IMPLEMENTATION"] = "dpc++"
        if self.options.hip_targets:
            tc.cache_variables["HIP_TARGETS"] = self.options.hip_targets
        tc.cache_variables["BUILD_FUNCTIONAL_TESTS"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        if self.options.mklcpu or self.options.mklgpu:
            tc.cache_variables["MKL_INCLUDE"] = self.dependencies["onemkl"].package_folder.replace("\\", "/") + "/include"
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.netlib_blas:
            deps.set_property("blas", "cmake_file_name", "NETLIB")
            deps.set_property("blas", "cmake_target_name", "ONEMATH::NETLIB::NETLIB")
        if self.options.armpl:
            deps.set_property("armpl", "cmake_file_name", "ARMPL")
            deps.set_property("armpl", "cmake_target_name", "ONEMKL::ARMPL::ARMPL")
        if self.options.cublas:
            deps.set_property("cublas", "cmake_target_name", "ONEMATH::cuBLAS::cuBLAS")
        if self.options.curand:
            deps.set_property("curand", "cmake_target_name", "ONEMATH::cuRAND::cuRAND")
        if self.options.cusolver:
            deps.set_property("cusolver", "cmake_target_name", "ONEMATH::cuSOLVER::cuSOLVER")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "oneMath")

        if self.options.mklcpu:
            self.cpp_info.components["onemath_blas_mklcpu"].set_property("cmake_target_name", "ONEMATH::onemath_blas_mklcpu")
            self.cpp_info.components["onemath_blas_mklcpu"].libs = ["onemath_blas_mklcpu"]
            self.cpp_info.components["onemath_blas_mklcpu"].requires = ["onemkl::mkl-sycl-blas"]

            self.cpp_info.components["onemath_lapack_mklcpu"].set_property("cmake_target_name", "ONEMATH::onemath_lapack_mklcpu")
            self.cpp_info.components["onemath_lapack_mklcpu"].libs = ["onemath_lapack_mklcpu"]
            self.cpp_info.components["onemath_lapack_mklcpu"].requires = ["onemkl::mkl-sycl-lapack"]

            self.cpp_info.components["onemath_rng_mklcpu"].set_property("cmake_target_name", "ONEMATH::onemath_rng_mklcpu")
            self.cpp_info.components["onemath_rng_mklcpu"].libs = ["onemath_rng_mklcpu"]
            self.cpp_info.components["onemath_rng_mklcpu"].requires = ["onemkl::mkl-sycl-rng"]

            self.cpp_info.components["onemath_dft_mklcpu"].set_property("cmake_target_name", "ONEMATH::onemath_dft_mklcpu")
            self.cpp_info.components["onemath_dft_mklcpu"].libs = ["onemath_dft_mklcpu"]
            self.cpp_info.components["onemath_dft_mklcpu"].requires = ["onemkl::mkl-sycl-dft"]

            self.cpp_info.components["onemath_sparse_blas_mklcpu"].set_property("cmake_target_name", "ONEMATH::onemath_sparse_blas_mklcpu")
            self.cpp_info.components["onemath_sparse_blas_mklcpu"].libs = ["onemath_sparse_blas_mklcpu"]
            self.cpp_info.components["onemath_sparse_blas_mklcpu"].requires = ["onemkl::mkl-sycl-sparse"]

        if self.options.mklgpu:
            self.cpp_info.components["onemath_blas_mklgpu"].set_property("cmake_target_name", "ONEMATH::onemath_blas_mklgpu")
            self.cpp_info.components["onemath_blas_mklgpu"].libs = ["onemath_blas_mklgpu"]
            self.cpp_info.components["onemath_blas_mklgpu"].requires = ["onemkl::mkl-sycl-blas"]

            self.cpp_info.components["onemath_lapack_mklgpu"].set_property("cmake_target_name", "ONEMATH::onemath_lapack_mklgpu")
            self.cpp_info.components["onemath_lapack_mklgpu"].libs = ["onemath_lapack_mklgpu"]
            self.cpp_info.components["onemath_lapack_mklgpu"].requires = ["onemkl::mkl-sycl-lapack"]

            self.cpp_info.components["onemath_rng_mklgpu"].set_property("cmake_target_name", "ONEMATH::onemath_rng_mklgpu")
            self.cpp_info.components["onemath_rng_mklgpu"].libs = ["onemath_rng_mklgpu"]
            self.cpp_info.components["onemath_rng_mklgpu"].requires = ["onemkl::mkl-sycl-rng"]

            self.cpp_info.components["onemath_dft_mklgpu"].set_property("cmake_target_name", "ONEMATH::onemath_dft_mklgpu")
            self.cpp_info.components["onemath_dft_mklgpu"].libs = ["onemath_dft_mklgpu"]
            self.cpp_info.components["onemath_dft_mklgpu"].requires = ["onemkl::mkl-sycl-dft"]

            self.cpp_info.components["onemath_sparse_blas_mklgpu"].set_property("cmake_target_name", "ONEMATH::onemath_sparse_blas_mklgpu")
            self.cpp_info.components["onemath_sparse_blas_mklgpu"].libs = ["onemath_sparse_blas_mklgpu"]
            self.cpp_info.components["onemath_sparse_blas_mklgpu"].requires = ["onemkl::mkl-sycl-sparse"]

        if self.options.netlib_blas:
            self.cpp_info.components["onemath_blas_netlib"].set_property("cmake_target_name", "ONEMATH::onemath_blas_netlib")
            self.cpp_info.components["onemath_blas_netlib"].libs = ["onemath_blas_netlib"]
            self.cpp_info.components["onemath_blas_netlib"].requires = ["blas::blas"]

        if self.options.armpl:
            for domain in ["blas", "lapack", "rng", "dft"]:
                name = f"onemath_{domain}_armpl"
                self.cpp_info.components[name].set_property("cmake_target_name", f"ONEMATH::{name}")
                self.cpp_info.components[name].libs = [name]
                self.cpp_info.components[name].requires = ["armpl::armpl"]

        if self.options.generic_sycl_blas:
            self.cpp_info.components["onemath_blas_generic"].set_property("cmake_target_name", "ONEMATH::onemath_blas_generic")
            self.cpp_info.components["onemath_blas_generic"].libs = ["onemath_blas_generic"]
            if self.options.generic_sycl_blas_tune == "intel_cpu":
                cxxflags = ["-fsycl-targets=spir64_x86_64", "-fsycl-unnamed-lambda"]
                ldflags = ["-fsycl-targets=spir64_x86_64"]
            elif self.options.generic_sycl_blas_tune == "intel_gpu":
                cxxflags = []
                ldflags = []
            elif self.options.generic_sycl_blas_tune == "amd_gpu":
                cxxflags = ["-fsycl-targets=amdgcn-amd-amdhsa", "-fsycl-unnamed-lambda", "-Xsycl-target-backend"]
                ldflags = ["-fsycl-targets=amdgcn-amd-amdhsa", "-Xsycl-target-backend"]
            elif self.options.generic_sycl_blas_tune == "nvidia_gpu":
                cxxflags = ["-fsycl-targets=nvptx64-nvidia-cuda", "-fsycl-unnamed-lambda"]
                ldflags = ["-fsycl-targets=nvptx64-nvidia-cuda"]
                if self.options.cuda_targets:
                    cxxflags.extend(["-Xsycl-target-backend", f"--cuda-gpu-arch={self.options.cuda_targets}"])
                    ldflags.extend(["-Xsycl-target-backend", f"--cuda-gpu-arch={self.options.cuda_targets}"])
            self.cpp_info.components["onemath_blas_generic"].cxxflags = cxxflags
            self.cpp_info.components["onemath_blas_generic"].sharedlinkflags = ldflags
            self.cpp_info.components["onemath_blas_generic"].exelinkflags = ldflags

        if self.options.cublas:
            self.cpp_info.components["onemath_blas_cublas"].set_property("cmake_target_name", "ONEMATH::onemath_blas_cublas")
            self.cpp_info.components["onemath_blas_cublas"].libs = ["onemath_blas_cublas"]
            self.cpp_info.components["onemath_blas_cublas"].requires = ["cublas::cublas_", "onemath_sycl"]

        if self.options.cusolver:
            self.cpp_info.components["onemath_lapack_cusolver"].set_property("cmake_target_name", "ONEMATH::onemath_lapack_cusolver")
            self.cpp_info.components["onemath_lapack_cusolver"].libs = ["onemath_lapack_cusolver"]
            self.cpp_info.components["onemath_lapack_cusolver"].requires = ["cusolver::cusolver_", "onemath_sycl"]

        if self.options.curand:
            self.cpp_info.components["onemath_rng_curand"].set_property("cmake_target_name", "ONEMATH::onemath_rng_curand")
            self.cpp_info.components["onemath_rng_curand"].libs = ["onemath_rng_curand"]
            self.cpp_info.components["onemath_rng_curand"].requires = ["curand::curand", "onemath_sycl"]

        if self.options.cufft:
            self.cpp_info.components["onemath_dft_cufft"].set_property("cmake_target_name", "ONEMATH::onemath_dft_cufft")
            self.cpp_info.components["onemath_dft_cufft"].libs = ["onemath_dft_cufft"]
            self.cpp_info.components["onemath_dft_cufft"].requires = ["cufft::cufft_", "onemath_sycl"]

        if self.options.cusparse:
            self.cpp_info.components["onemath_sparse_blas_cusparse"].set_property("cmake_target_name", "ONEMATH::onemath_sparse_blas_cusparse")
            self.cpp_info.components["onemath_sparse_blas_cusparse"].libs = ["onemath_sparse_blas_cusparse"]
            self.cpp_info.components["onemath_sparse_blas_cusparse"].requires = ["cusparse::cusparse", "onemath_sycl"]

        if self.options.portfft:
            self.cpp_info.components["onemath_dft_portfft"].set_property("cmake_target_name", "ONEMATH::onemath_dft_portfft")
            self.cpp_info.components["onemath_dft_portfft"].libs = ["onemath_dft_portfft"]
            self.cpp_info.components["onemath_dft_portfft"].requires = ["portfft::portfft"]

        # Dynamic loader library
        if self.options.shared:
            self.cpp_info.components["onemath_dynamic"].set_property("cmake_target_name", "ONEMATH::onemath")
            self.cpp_info.components["onemath_dynamic"].libs = ["onemath"]

        sycl = self.cpp_info.components["onemath_sycl"]
        sycl.set_property("cmake_target_name", "ONEMATH::SYCL::SYCL")
        sycl.requires = ["intel-dpcpp-sycl::intel-dpcpp-sycl"]
        sycl.cxxflags = ["-fsycl"]
        if self.settings.os != "Windows":
            ldflags = ["-fsycl"]
            if any(self.options.get_safe(backend) for backend in ["cublas", "curand", "cusolver", "cufft", "cusparse"]):
                sycl.cxxflags.extend(["-fsycl-targets=nvptx64-nvidia-cuda", "-fsycl-unnamed-lambda"])
                ldflags.extend(["-fsycl-targets=nvptx64-nvidia-cuda"])
            elif any(self.options.get_safe(backend) for backend in ["rocblas", "rocrand", "rocsolver", "rocfft", "rocparse"]):
                sycl.cxxflags.extend(["-fsycl-targets=amdgcn-amd-amdhsa", "-fsycl-unnamed-lambda", "-Xsycl-target-backend"])
                ldflags.extend(["-fsycl-targets=amdgcn-amd-amdhsa", "-Xsycl-target-backend"])
                if self.options.hip_targets:
                    sycl.cxxflags.append(f"--offload-arch={self.options.hip_targets}")
                    ldflags.append(f"--offload-arch={self.options.hip_targets}")
            sycl.sharedlinkflags.extend(ldflags)
            sycl.exelinkflags.extend(ldflags)

        for name, _ in self.cpp_info.components.items():
            if name != "onemath_sycl":
                self.cpp_info.components[name].requires.append("onemath_sycl")

        # TODO:
        # onemath_blas_armpl
        # onemath_blas_rocblas
        # onemath_dft_rocfft
        # onemath_lapack_armpl
        # onemath_lapack_rocsolver
        # onemath_rng_armpl
        # onemath_rng_rocrand
        # onemath_sparse_blas_rocsparse
