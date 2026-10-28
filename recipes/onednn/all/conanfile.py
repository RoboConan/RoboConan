import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.21"


class OneDNNConan(ConanFile):
    name = "onednn"
    description = ("oneAPI Deep Neural Network Library (oneDNN) is an open-source cross-platform "
                   "performance library of basic building blocks for deep learning applications.")
    license = "Apache-2.0"
    homepage = "https://github.com/uxlfoundation/oneDNN"
    topics = ("oneapi", "dnn", "deep-learning", "sycl")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_graph_api": [True, False],
        "workload": ["training", "inference"],
        "cpu_runtime": ["none", "omp", "tbb", "sycl", "threadpool", "seq"],
        "gpu_runtime": ["none", "ocl", "sycl", "ze"],
        "gpu_vendor": ["none", "intel", "nvidia", "amd", "generic"],
        "blas_vendor": ["internal", "accelerate", "armpl", "external"],
        "enable_concurrent_exec": [True, False],
        "enable_experimental_grouped_memory": [True, False],
        "enable_experimental_logging": [True, False],
        "enable_experimental_profiling": [True, False],
        "enable_experimental_sycl_profiling_tag": [True, False],
        "safe_rbp": [True, False],
        "with_kleidiai": [True, False],
        "install_dev_headers": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_graph_api": True,
        "workload": "training",
        "cpu_runtime": "omp",  # sycl for Intel compilers
        "gpu_runtime": "ocl",  # sycl for Intel compilers
        "gpu_vendor": "intel",
        "blas_vendor": "internal",
        "enable_concurrent_exec": False,
        "enable_experimental_grouped_memory": False,
        "enable_experimental_logging": False,
        "enable_experimental_profiling": False,
        "enable_experimental_sycl_profiling_tag": False,
        "safe_rbp": False,
        "with_kleidiai": True,
        "install_dev_headers": False,
    }
    options_description = {
        "workload": ("Specifies a set of functionality to be available at build time. "
                     "Designed to decrease the final disk footprint. Valid values:"
                     "- 'training' (the default). Includes all functionality to be enabled."
                     "- 'inference'. Includes only forward propagation kind functionality and their dependencies."),
        "cpu_runtime": ("Specifies the threading runtime for CPU engines. "
                       "Supports OMP (default), TBB or SYCL (SYCL CPU engines)."),
        "gpu_runtime": ("Specifies the threading runtime for GPU engines."
                        "Can be NONE (no GPU engines), OCL (default; OpenCL GPU engines), "
                        "SYCL (SYCL GPU engines), or ZE (Level Zero GPU engines)."),
        "gpu_vendor": "Specifies target GPU vendor for GPU engines. Can be INTEL (default), NVIDIA, AMD, or GENERIC.",
        "blas_vendor": ("BLAS library to use. Options are: "
                        "- 'internal' (default). Use internal BLAS implementation. Recommended in most situations."
                        "- 'accelerate'. Use Apple Accelerate framework on macOS."
                        "- 'armpl'. Use Arm Performance Libraries on Arm platforms."
                        "- 'external'. Use an external BLAS library. This vendor is supported for performance analysis purposes only."),
        "enable_concurrent_exec": ("Disables sharing a common scratchpad between primitives. "
                                   "This option must be turned on if there is a possibility of executing distinct primitives concurrently. "
                                   "CAUTION: enabling this option increases memory consumption."),
        "enable_experimental_profiling": "Enable experimental profiling capabilities.",
        "enable_experimental_grouped_memory": "Enable experimental grouped memory format and grouped GEMM support.",
        "enable_experimental_logging": "Enable experimental logging support.",
        "enable_experimental_sycl_profiling_tag": "Enable verbose profiling through the SYCL profiling-tag extension.",
        "safe_rbp": "Prohibit RBP register clobbering in JIT kernels.",
        "with_kleidiai": "Enable AArch64 KleidiAI-based implementations.",
        "install_dev_headers": "Install internal headers in addition to public ones (for OpenVINO recipe).",
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not str(self.settings.arch).startswith("armv8"):
            del self.options.with_kleidiai
        if self.settings.compiler == "intel-cc" and self.settings.compiler.mode in ["icx", "dpcpp"]:
            # Intel compiler users can take advantage of SYCL support
            self.options.cpu_runtime = "sycl"
            self.options.gpu_runtime = "sycl"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.gpu_runtime == "none":
            del self.options.gpu_vendor
        elif self.options.gpu_runtime == "ze":
            self.options.build_graph_api.value = False
        if (self.options.get_safe("with_kleidiai")
                and (self.options.cpu_runtime == "threadpool" or self.settings.compiler == "msvc")):
            self.options.with_kleidiai.value = False
        if self.options.get_safe("with_kleidiai"):
            self.options["kleidiai"].experimental_ops = True
        if self.options.get_safe("gpu_vendor") != "nvidia":
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.cpu_runtime == "omp":
            self.requires("openmp/system")
        elif self.options.cpu_runtime == "tbb":
            self.requires("onetbb/[>=2021]")
        elif self.options.cpu_runtime == "sycl":
            self.requires(f"intel-dpcpp-sycl/[~{self.settings.compiler.version}]")
        if self.options.gpu_runtime == "ocl":
            self.requires("opencl-icd-loader/[*]")
        if self.options.gpu_runtime in ["ocl", "ze"]:
            self.requires("opencl-headers/[*]", transitive_headers=True)
        elif self.options.gpu_runtime == "sycl" and self.options.cpu_runtime != "sycl":
            self.requires(f"intel-dpcpp-sycl/[~{self.settings.compiler.version}]")
        if self.options.get_safe("gpu_vendor") == "nvidia":
            self.cuda.requires("cublas")
            self.requires("cudnn/[>=8 <10]")

        # Unvendored third-party dependencies
        if (self.options.gpu_runtime in ["sycl", "ze"]
                and self.options.get_safe("gpu_vendor") == "intel"):
            self.requires("level-zero/[^1.17]", transitive_headers=True)
        if self.options.enable_experimental_logging:
            self.requires("spdlog/[^1.11]")
        if self.options.blas_vendor != "internal":
            self.requires("blas/latest")
        if self.settings.arch in ["x86", "x86_64"] or str(self.settings.arch).startswith("armv8"):
            self.requires("ittapi/[^3.23.0]")
        if self.settings.arch in ["x86", "x86_64"]:
            self.requires("xbyak/[^7.40]")
        elif str(self.settings.arch).startswith("armv8"):
            self.requires("xbyak_aarch64/[^1.1.2]")
            if self.options.with_kleidiai:
                self.requires("kleidiai/[^1.30]")
        elif self.settings.arch == "riscv64":
            self.requires("xbyak_riscv/[^6.68]")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.options.cpu_runtime == "sycl" or self.options.gpu_runtime == "sycl":
            if self.settings.compiler != "intel-cc" or self.settings.compiler.mode not in ["icx", "dpcpp"]:
                raise ConanInvalidConfiguration("SYCL runtime is only supported with Intel icpx or dpcpp compilers.")
            if self.options.cpu_runtime == "sycl" and self.options.gpu_runtime != "sycl":
                raise ConanInvalidConfiguration("SYCL CPU runtime requires matching SYCL GPU runtime.")
        if self.options.build_graph_api and self.options.get_safe("gpu_vendor", "none") not in ["none", "intel", "nvidia"]:
            raise ConanInvalidConfiguration("enable_graph_api can only be used with gpu_vendor set to 'none', 'intel' or 'nvidia'.")
        if self.options.blas_vendor == "accelerate" and self.settings.os != "Macos":
            raise ConanInvalidConfiguration("blas_vendor=accelerate is only supported on macOS.")
        if self.options.blas_vendor == "armpl":
            if not str(self.settings.arch).startswith("armv8"):
                raise ConanInvalidConfiguration("blas_vendor=armpl is only supported on Arm64.")
            if self.dependencies["blas"].options.provider != "armpl":
                raise ConanInvalidConfiguration("blas_vendor=armpl requires blas:provider=armpl")
        if self.options.blas_vendor == "accelerate" and self.dependencies["blas"].options.provider != "accelerate":
            raise ConanInvalidConfiguration("blas_vendor=accelerate requires blas:provider=accelerate")
        if self.options.gpu_runtime != "none" and self.options.get_safe("gpu_vendor") == "none":
            raise ConanInvalidConfiguration("A GPU vendor must be selected when the GPU runtime is enabled")
        if self.options.gpu_runtime == "ze" and self.options.gpu_vendor != "intel":
            raise ConanInvalidConfiguration("The Level Zero GPU runtime only supports Intel GPUs")
        if (self.options.get_safe("with_kleidiai")
                and not self.dependencies["kleidiai"].options.experimental_ops):
            raise ConanInvalidConfiguration("with_kleidiai requires kleidiai:experimental_ops=True")
        if self.options.get_safe("gpu_vendor") == "nvidia":
            self.cuda.validate_settings()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18]")
        if self.options.get_safe("gpu_vendor") == "nvidia":
            self.cuda.tool_requires("nvcc")

    def source(self):
        info = self.conan_data["sources"][self.version]
        get(self, **info["onednn"], strip_root=True)
        apply_conandata_patches(self)
        rmdir(self, "third_party/ittnotify")
        rmdir(self, "third_party/kleidiai")
        rmdir(self, "third_party/level_zero")
        rmdir(self, "third_party/opencl")
        rmdir(self, "third_party/spdlog")
        rmdir(self, "third_party/xbyak")
        rmdir(self, "third_party/xbyak_aarch64")
        rmdir(self, "third_party/xbyak_riscv")
        # Replace two vendored headers with the latest versions from intel/compute-runtime
        download(self, **info["ze_intel_gpu.h"], filename="third_party/level_zero/ze_intel_gpu.h")
        download(self, **info["ze_stypes.h"], filename="third_party/level_zero/ze_stypes.h")
        rm(self, "FindcuBLAS.cmake", "cmake")
        rm(self, "FindcuBLASLt.cmake", "cmake")
        rm(self, "FindcuDNN.cmake", "cmake")
        # Don't try to install FindcuBLAS.cmake, etc.
        replace_in_file(self, "src/CMakeLists.txt", "if(DNNL_SYCL_CUDA)", "if(0)")
        # Don't need to adjust import target order for Conan
        replace_in_file(self, "cmake/SYCL.cmake",
                        "adjust_headers_priority(",
                        "# adjust_headers_priority(")
        # linked libraries are not propagated correctly for CUDA otherwise
        replace_in_file(self, "cmake/SYCL.cmake",
                        "list(APPEND EXTRA_SHARED_LIBS cuBLAS::cuBLAS",
                        "link_libraries(cuBLAS::cuBLAS")

    @property
    def _blas_vendor(self):
        return {
            "internal": "NONE",
            "accelerate": "ACCELERATE",
            "armpl": "ARMPL",
            "external": "ANY",
        }[str(self.options.blas_vendor)]

    def generate(self):
        # https://github.com/uxlfoundation/oneDNN/blob/v3.14/cmake/options.cmake
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.cache_variables["ONEDNN_LIBRARY_TYPE"] = "SHARED" if self.options.shared else "STATIC"
        tc.cache_variables["ONEDNN_BUILD_DOC"] = False
        tc.cache_variables["ONEDNN_BUILD_EXAMPLES"] = False
        tc.cache_variables["ONEDNN_BUILD_TESTS"] = False
        tc.cache_variables["ONEDNN_BUILD_GRAPH"] = self.options.build_graph_api
        tc.cache_variables["ONEDNN_ENABLE_WORKLOAD"] = str(self.options.workload).upper()
        tc.cache_variables["ONEDNN_CPU_RUNTIME"] = str(self.options.cpu_runtime).upper()
        tc.cache_variables["ONEDNN_GPU_RUNTIME"] = str(self.options.gpu_runtime).upper()
        tc.cache_variables["ONEDNN_GPU_VENDOR"] = str(self.options.get_safe("gpu_vendor", "intel")).upper()
        tc.cache_variables["ONEDNN_BLAS_VENDOR"] = self._blas_vendor
        tc.cache_variables["ONEDNN_ENABLE_CONCURRENT_EXEC"] = self.options.enable_concurrent_exec
        tc.cache_variables["ONEDNN_EXPERIMENTAL_GROUPED_MEMORY"] = self.options.enable_experimental_grouped_memory
        tc.cache_variables["ONEDNN_EXPERIMENTAL_LOGGING"] = self.options.enable_experimental_logging
        tc.cache_variables["ONEDNN_EXPERIMENTAL_PROFILING"] = self.options.enable_experimental_profiling
        tc.cache_variables["ONEDNN_EXPERIMENTAL_ENABLE_SYCL_PROFILING_TAG"] = self.options.enable_experimental_sycl_profiling_tag
        tc.cache_variables["ONEDNN_SAFE_RBP"] = self.options.safe_rbp
        tc.cache_variables["ONEDNN_AARCH64_USE_KAI"] = self.options.get_safe("with_kleidiai", False)
        if self.options.gpu_runtime in ["ocl", "ze"]:
            tc.cache_variables["ONEDNN_OCL_INCLUDE_DIR"] = self.dependencies["opencl-headers"].cpp_info.includedirs[0]
        if (self.options.gpu_runtime in ["sycl", "ze"]
                and self.options.get_safe("gpu_vendor") == "intel"):
            tc.cache_variables["ONEDNN_ZE_INCLUDE_DIR"] = os.path.join(self.build_folder, "level-zero")
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.get_safe("gpu_vendor") == "nvidia":
            deps.set_property("cublas::cublas_", "cmake_target_name", "cuBLAS::cuBLAS")
            deps.set_property("cublas::cublasLt", "cmake_target_name", "cublasLt::cublasLt")
        deps.generate()

        if self.options.get_safe("gpu_vendor") == "nvidia":
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def build(self):
        if self.options.gpu_runtime in ["sycl", "ze"] and self.options.get_safe("gpu_vendor") == "intel":
            level_zero_include = os.path.join(self.build_folder, "level-zero", "level_zero")
            copy(self, "*.h", os.path.join(self.dependencies["level-zero"].package_folder, "include", "level_zero"), level_zero_include)
            copy(self, "*.h", os.path.join(self.source_folder, "third_party", "level_zero"), level_zero_include)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "THIRD-PARTY-PROGRAMS", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

        # Install dev headers for OpenVINO onednn extensions
        if self.options.install_dev_headers:
            subdirs = ["common"]
            if self.options.cpu_runtime != "none":
                subdirs.append("cpu")
            if self.options.gpu_runtime != "none":
                subdirs.append("gpu")
            for subdir in subdirs:
                copy(self, "*.h*",
                     os.path.join(self.source_folder, "src", subdir),
                     os.path.join(self.package_folder, "include", "dnnl_dev", subdir))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dnnl")
        self.cpp_info.set_property("cmake_target_name", "DNNL::dnnl")
        cpu_runtime = str(self.options.cpu_runtime).upper()
        if self.options.cpu_runtime == "none":
            cpu_threading_runtime = "SEQ"
        elif self.options.cpu_runtime == "sycl":
            cpu_threading_runtime = "TBB"
        else:
            cpu_threading_runtime = cpu_runtime
        self.cpp_info.set_property("cmake_extra_variables", {
            "DNNL_CPU_RUNTIME": cpu_runtime,
            "DNNL_CPU_THREADING_RUNTIME": cpu_threading_runtime,
            "DNNL_GPU_RUNTIME": str(self.options.gpu_runtime).upper(),
            "DNNL_BLAS_VENDOR": self._blas_vendor,
            "DNNL_GPU_VENDOR": str(self.options.get_safe("gpu_vendor", "intel")).upper(),
        })
        self.cpp_info.libs = ["dnnl"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        if self.options.install_dev_headers:
            self.cpp_info.includedirs.append(os.path.join("include", "dnnl_dev"))

        # For the dnnl C API
        if not self.options.shared and stdcpp_library(self):
            self.cpp_info.system_libs.append(stdcpp_library(self))

        if self.options.cpu_runtime == "sycl" or self.options.gpu_runtime == "sycl":
            self.cpp_info.cxxflags.append("-fsycl")
