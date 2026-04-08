import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime

required_conan_version = ">=2.1"


class LibtorchConan(ConanFile):
    name = "libtorch"
    description = "Tensors and Dynamic neural networks with strong GPU acceleration"
    license = "BSD-3-Clause"
    homepage = "https://pytorch.org"
    topics = ("machine-learning", "deep-learning", "neural-network", "gpu", "tensor")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "blas": ["generic", "eigen"],
        "build_lazy_ts_backend": [True, False],
        "build_lite_interpreter": [True, False],
        "per_operator_headers": [True, False],
        "utilities": [True, False],
        "with_acl": [True, False],
        "with_fbgemm": [True, False],
        "with_gflags": [True, False],
        "with_glog": [True, False],
        "with_itt": [True, False],
        "with_mimalloc": [True, False],
        "with_numa": [True, False],
        "with_openmp": [True, False],
        "with_nnpack": [True, False],
        "build_qnnpack": [True, False],
        "with_xnnpack": [True, False],
        # CUDA
        "with_cuda": [True, False],
        "with_cudnn": [True, False],
        "with_cudss": [True, False],
        "with_cufile": [True, False],
        "with_cusparselt": [True, False],
        "with_nvrtc": [True, False],
        "with_nccl": [True, False],
        "build_lazy_cuda_linalg": [True, False],
        # Distributed
        "distributed": [True, False],
        "with_gloo": [True, False],
        "with_mpi": [True, False],
        "with_tensorpipe": [True, False],
        "with_ucc": [True, False],
        "with_nvshmem": [True, False],
        # Other backends
        "with_coreml": [True, False],
        "with_metal": [True, False],
        "with_mps": [True, False],
        "with_opencl": [True, False],
        "with_onednn": [True, False],
        "with_kleidiai": [True, False],
        # "with_nnapi": [True, False],
        # "with_rocm": [True, False],
        # "with_snpe": [True, False],
        # "with_vulkan": [True, False],
        # "with_xpu": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "blas": "generic",
        "build_lazy_ts_backend": True,
        "build_lite_interpreter": False,
        "per_operator_headers": False,
        "utilities": False,
        "with_acl": True,
        "with_fbgemm": True,
        "with_gflags": True,
        "with_glog": True,
        "with_itt": False,
        "with_mimalloc": False,
        "with_numa": True,
        "with_openmp": True,
        "with_nnpack": False,
        "build_qnnpack": False,
        "with_xnnpack": True,
        # CUDA
        "with_cuda": False,
        "with_cudnn": True,
        "with_cudss": True,
        "with_cufile": True,
        "with_cusparselt": True,
        "with_nvrtc": True,
        "with_nccl": True,
        "build_lazy_cuda_linalg": False,
        # Distributed
        "distributed": False,
        "with_gloo": True,
        "with_mpi": False,
        "with_tensorpipe": False,
        "with_ucc": False,
        "with_nvshmem": False,
        # Other backends
        "with_coreml": False,
        "with_metal": False,
        "with_mps": False,
        "with_opencl": True,
        "with_onednn": False,
        "with_kleidiai": True,
        "openmpi/*:with_cuda": True,
        "libfabric/*:shared": True,  # for nvshmem
    }
    no_copy_source = True

    python_requires = ["conan-cuda/latest", "conan-utils/latest"]
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    @property
    def _is_mobile_os(self):
        return self.settings.os in ["Android", "iOS"]

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        copy(self, "conan-official-libtorch-vars.cmake", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not is_apple_os(self):
            del self.options.with_coreml
            del self.options.with_metal
            del self.options.with_mps
        if self.settings.os != "Linux":
            del self.options.with_numa
        if self.settings.os != "Android":
            self.options.rm_safe("with_nnapi")
            self.options.rm_safe("with_snpe")
            self.options.rm_safe("with_vulkan")
        if self._is_mobile_os:
            self.options.blas = "eigen"
            self.options.build_lazy_ts_backend = False
            del self.options.distributed
        if self.settings.arch not in ["x86", "x86_64"]:
            # armv8 is not yet supported
            self.options.with_fbgemm = False
        if self.settings.arch != "armv8":
            del self.options.with_acl
        self.options.with_itt = self.settings.arch in ["x86", "x86_64"]

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda
            del self.options.build_lazy_cuda_linalg
            del self.options.with_cudnn
            del self.options.with_cudss
            del self.options.with_cufile
            del self.options.with_cusparselt
            del self.options.with_nvrtc
            del self.options.with_nccl
            del self.options.with_nvshmem
        else:
            if self.options.get_safe("with_gloo"):
                self.options["gloo"].with_cuda = True
            if self.options.get_safe("with_tensorpipe"):
                self.options["tensorpipe"].cuda = True
        if not self.options.get_safe("distributed"):
            del self.options.with_gloo
            del self.options.with_mpi
            del self.options.with_tensorpipe
            del self.options.with_ucc
            self.options.rm_safe("with_nvshmem")
        if not self.options.with_onednn:
            self.options.rm_safe("with_acl")
        if self.options.build_qnnpack:
            self.provides = ["qnnpack"]

        # numa static can't be linked into shared libs.
        # Because Caffe2_detectron_ops* libs are always shared, we have to force
        # numa shared even if libtorch:shared=False
        if self.options.get_safe("with_numa"):
            self.options["libnuma"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _require_sleef(self):
        return not self._is_mobile_os and not self.settings.os == "Emscripten"

    @property
    def _require_flatbuffers(self):
        return not self._is_mobile_os

    @property
    def _blas_cmake_option_value(self):
        if self.options.blas == "eigen":
            return "Eigen"
        blas_provider = str(self.dependencies["blas"].options.provider)
        return {
            "accelerate": "accelerate",
            "armpl": "APL",
            "atlas": "ATLAS",
            "blis": "FLAME",
            "mkl": "MKL",
            "openblas": "OpenBLAS",
        }[blas_provider]

    @property
    def _use_nnpack_family(self):
        return any(self.options.get_safe(f"with_{name}") for name in ["nnpack", "qnnpack", "xnnpack"])

    def requirements(self):
        self.requires("concurrentqueue/[^1.0]", transitive_headers=True, transitive_libs=True)
        self.requires("cpp-httplib/[>=0.18.0 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("cpuinfo/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/[>=3.3 <6]")
        self.requires("fmt/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("kineto/[>=0.4.0 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("libbacktrace/[*]")
        self.requires("miniz/3.0.2-pytorch")
        self.requires("nlohmann_json/[^3]", transitive_headers=True)
        self.requires("onnx/[^1.13]", transitive_headers=True, transitive_libs=True)
        self.requires("protobuf/[>=3.21.12]")
        self.requires("pocketfft/[*]")
        if self._require_sleef:
            self.requires("sleef/[^3.6.1]", transitive_headers=True, transitive_libs=True)
        if self._require_flatbuffers:
            self.requires("flatbuffers/[~24.3.25]", libs=False, transitive_headers=True)
        if self.options.blas == "generic":
            self.requires("lapack/latest")
        if self.options.with_openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.with_fbgemm:
            self.requires("fbgemm/[^1.1.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_gflags:
            self.requires("gflags/[^2.2.2]", transitive_headers=True, transitive_libs=True)
        if self.options.with_glog:
            self.requires("glog/[~0.6]", transitive_headers=True, transitive_libs=True)
        if self.options.with_xnnpack:
            self.requires("xnnpack/0.0+git.20241203", transitive_headers=True, transitive_libs=True)
        if self.options.build_qnnpack:
            # PyTorch's QNNPACK has significant modifications and can't be unvendored
            self.requires("fp16/[*]")
            self.requires("fxdiv/[*]")
            self.requires("psimd/[*]")
            self.requires("pthreadpool/[*]")
        if self.options.with_nnpack:
            self.requires("nnpack/[*]")
        if self.options.with_onednn:
            self.requires("ideep/[>=3.0]", transitive_headers=True, transitive_libs=True)
            if self.options.get_safe("with_acl"):
                self.requires("arm-compute-library/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.with_itt:
            self.requires("ittapi/[^3.23.0]")
        if self.options.get_safe("with_numa"):
            self.requires("libnuma/[^2.0.16]")
        if self.options.with_opencl:
            self.requires("opencl-icd-loader/[*]")
        if self.options.get_safe("with_vulkan"):
            self.requires("vulkan-loader/[^1.3.239.0]")
        if self.options.with_mimalloc:
            self.requires("mimalloc/[^2.1.7]")
        if self.options.get_safe("distributed"):
            if self.options.with_gloo:
                self.requires("gloo/[>=0.5.0 <1]")
            if self.options.with_mpi:
                self.requires("openmpi/[>=4 <6]")
            if self.options.with_tensorpipe:
                self.requires("tensorpipe/[*]")
            if self.options.with_ucc:
                self.requires("ucc/[^1.5.0]")
        if self.options.with_cuda:
            self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)
            self.cuda.requires("cublas", transitive_headers=True, transitive_libs=True)
            self.cuda.requires("cufft", transitive_headers=True, transitive_libs=True)
            self.cuda.requires("curand", transitive_headers=True, transitive_libs=True)
            self.cuda.requires("nvml-stubs", transitive_headers=True, transitive_libs=True)
            self.cuda.requires("nvtx", transitive_headers=True, transitive_libs=True)
            self.cuda.requires("cusparse", transitive_headers=True, transitive_libs=True)
            self.requires("cutlass/[*]", transitive_headers=True, transitive_libs=True)
            if self.options.with_cusparselt:
                self.cuda.requires("cusparselt")
            if not self.options.build_lazy_cuda_linalg:
                self.cuda.requires("cusolver")
            if self.options.with_cudnn:
                self.requires("cudnn/[>=8.5 <10]", transitive_headers=True, transitive_libs=True)
                self.requires("cudnn-frontend/[^1.13]", transitive_headers=True, transitive_libs=True)
            if self.options.with_cudss:
                self.cuda.requires("cudss")
            if self.options.with_cufile:
                self.cuda.requires("cufile")
            if self.options.with_nvrtc:
                self.cuda.requires("nvrtc", transitive_headers=True, transitive_libs=True)
            if self.options.with_nccl:
                self.requires("nccl/[^2]", transitive_headers=True, transitive_libs=True)
            if self.options.get_safe("with_nvshmem"):
                self.requires("nvshmem/[^3]")

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 11)
        if self.options.get_safe("with_mpi") and not self.dependencies["openmpi"].options.with_cuda:
            raise ConanInvalidConfiguration("openmpi must be built with CUDA support (-o openmpi/*:with_cuda=True)")
        miniz_dep = self.dependencies["miniz"]
        if "pytorch" not in str(miniz_dep.ref.version):
            raise ConanInvalidConfiguration("miniz must be built with a custom 'pytorch' version")
        if not miniz_dep.options.disable_crc32_checks:
            raise ConanInvalidConfiguration("miniz must be built with '-o miniz/*:disable_crc32_checks=True'")
        if not miniz_dep.options.use_external_mzcrc:
            raise ConanInvalidConfiguration("miniz must be built with '-o miniz/*:use_external_mzcrc=True'")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.27]")
        # self.tool_requires("cpython/[^3.12]")
        if self._require_flatbuffers:
            self.tool_requires("flatbuffers/<host_version>")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["pytorch"], strip_root=True)
        apply_conandata_patches(self)
        rmdir(self, "third_party")
        get(self, **self.conan_data["sources"][self.version]["flash-attention"], strip_root=True,
            destination="third_party/flash-attention")
        # Recreate some for add_subdirectory() to work
        for pkg in ["fmt", "FXdiv", "kineto/libkineto", "mimalloc", "tensorpipe"]:
            save(self, os.path.join("third_party", pkg, "CMakeLists.txt"), "")
        # Use FindOpenMP from Conan or CMake
        rm(self, "FindOpenMP.cmake", "cmake/modules")
        # No need for this broken workaround anymore since glog v0.6.0
        replace_in_file(self, "c10/util/Logging.cpp",
                        "google::glog_internal_namespace_::IsGoogleLoggingInitialized()",
                        "google::IsGoogleLoggingInitialized()")
        # Don't need to explicitly link against fxdiv
        replace_in_file(self, "caffe2/CMakeLists.txt", "TARGET_LINK_LIBRARIES(torch_cpu PRIVATE fxdiv)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_Torch_INCLUDE"] = "conan_deps.cmake"
        tc.cache_variables["ATEN_NO_TEST"] = True
        tc.cache_variables["BUILD_BINARY"] = self.options.utilities
        tc.cache_variables["BUILD_CUSTOM_PROTOBUF"] = False
        tc.cache_variables["BUILD_PYTHON"] = False
        tc.cache_variables["BUILD_LITE_INTERPRETER"] = self.options.build_lite_interpreter
        tc.cache_variables["CAFFE2_USE_MSVC_STATIC_RUNTIME"] = is_msvc_static_runtime(self)
        tc.cache_variables["BUILD_TEST"] = False
        tc.cache_variables["BUILD_AOT_INDUCTOR_TEST"] = False
        tc.cache_variables["BUILD_STATIC_RUNTIME_BENCHMARK"] = False
        tc.cache_variables["BUILD_MOBILE_BENCHMARK"] = False
        tc.cache_variables["BUILD_MOBILE_TEST"] = False
        tc.cache_variables["BUILD_JNI"] = False
        tc.cache_variables["BLAS"] = self._blas_cmake_option_value
        tc.cache_variables["USE_XPU"] = self.options.get_safe("with_xpu", False)
        tc.cache_variables["USE_CUDA"] = self.options.with_cuda
        tc.cache_variables["USE_ROCM"] = self.options.get_safe("with_rocm", False)
        if self.options.with_cuda:
            tc.cache_variables["BUILD_LAZY_CUDA_LINALG"] = self.options.build_lazy_cuda_linalg
            tc.cache_variables["USE_CUDNN"] = self.options.with_cudnn
            tc.cache_variables["USE_CUSPARSELT"] = self.options.with_cusparselt
            tc.cache_variables["USE_CUDSS"] = self.options.with_cudss
            tc.cache_variables["USE_CUFILE"] = self.options.with_cufile
            tc.cache_variables["USE_NVRTC"] = self.options.with_nvrtc
            tc.cache_variables["USE_NCCL"] = self.options.with_nccl
            tc.cache_variables["USE_NVSHMEM"] = self.options.get_safe("with_nvshmem", False)
        tc.cache_variables["USE_FBGEMM"] = self.options.with_fbgemm
        tc.cache_variables["USE_KINETO"] = True  # can't really be disabled
        tc.cache_variables["USE_FAKELOWP"] = False  # not actually used anywhere
        tc.cache_variables["USE_GFLAGS"] = self.options.with_gflags
        tc.cache_variables["USE_GLOG"] = self.options.with_glog
        tc.cache_variables["USE_LITE_PROTO"] = self.dependencies["protobuf"].options.lite
        tc.cache_variables["USE_MAGMA"] = False
        tc.cache_variables["USE_PYTORCH_METAL"] = self.options.get_safe("with_metal", False)
        tc.cache_variables["USE_PYTORCH_METAL_EXPORT"] = self.options.get_safe("with_metal", False)
        tc.cache_variables["USE_NATIVE_ARCH"] = False
        tc.cache_variables["USE_MPS"] = self.options.get_safe("with_mps")
        tc.cache_variables["USE_XCCL"] = self.options.get_safe("with_xccl", False)
        tc.cache_variables["USE_RCCL"] = self.options.get_safe("with_rccl", False)
        tc.cache_variables["USE_NNAPI"] = self.options.get_safe("with_nnapi", False)
        tc.cache_variables["USE_NUMA"] = self.options.get_safe("with_numa", False)
        tc.cache_variables["USE_NUMPY"] = False
        tc.cache_variables["USE_OPENCL"] = self.options.with_opencl
        tc.cache_variables["USE_OPENMP"] = self.options.with_openmp
        tc.cache_variables["USE_PROF"] = False  # requires htrace
        tc.cache_variables["USE_SNPE"] = self.options.get_safe("with_snpe", False)
        tc.cache_variables["USE_VALGRIND"] = False
        tc.cache_variables["USE_VULKAN"] = self.options.get_safe("with_vulkan", False)
        tc.cache_variables["USE_NNPACK"] = self.options.with_nnpack
        tc.cache_variables["USE_PYTORCH_QNNPACK"] = self.options.build_qnnpack
        tc.cache_variables["USE_XNNPACK"] = self.options.with_xnnpack
        tc.cache_variables["USE_ITT"] = self.options.with_itt
        tc.cache_variables["USE_MKLDNN"] = self.options.with_onednn
        tc.cache_variables["USE_MKLDNN_ACL"] = self.options.get_safe("with_acl", False)
        tc.cache_variables["USE_DISTRIBUTED"] = self.options.get_safe("distributed", False)
        if self.options.get_safe("distributed"):
            tc.cache_variables["USE_MPI"] = self.options.with_mpi
            tc.cache_variables["USE_UCC"] = self.options.with_ucc
            tc.cache_variables["USE_SYSTEM_UCC"] = self.options.with_ucc
            tc.cache_variables["USE_GLOO"] = self.options.with_gloo
            tc.cache_variables["USE_TENSORPIPE"] = self.options.with_tensorpipe
        tc.cache_variables["HAVE_SOVERSION"] = True
        tc.cache_variables["USE_CCACHE"] = False
        tc.cache_variables["WERROR"] = False
        tc.cache_variables["USE_COREML_DELEGATE"] = self.options.get_safe("with_coreml", False)
        tc.cache_variables["BUILD_LAZY_TS_BACKEND"] = self.options.build_lazy_ts_backend
        tc.cache_variables["BUILD_FUNCTORCH"] = False  # TODO: add as an option
        tc.cache_variables["BUILD_BUNDLE_PTXAS"] = False  # TODO: add as an option?
        tc.cache_variables["USE_KLEIDIAI"] = self.options.get_safe("with_kleidiai", False)
        tc.cache_variables["USE_MIMALLOC"] = self.options.with_mimalloc
        tc.cache_variables["USE_LLVM"] = False
        tc.cache_variables["USE_SYSTEM_LIBS"] = True
        tc.cache_variables["CONAN_LIBTORCH_USE_FLATBUFFERS"] = self._require_flatbuffers
        tc.cache_variables["CONAN_LIBTORCH_USE_SLEEF"] = self._require_sleef
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        # These try_compile checks fail with a static OpenBLAS for some reason
        if self.options.blas == "generic":
            tc.cache_variables["ACCELERATE_LAPACK_WORKS"] = True
            tc.cache_variables["APL_LAPACK_WORKS"] = True
            tc.cache_variables["FLEXIBLAS_LAPACK_WORKS"] = True
            tc.cache_variables["OPEN_LAPACK_WORKS"] = True
            tc.cache_variables["LAPACK_CGESDD_WORKS"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("concurrentqueue", "cmake_target_name", "moodycamel")
        deps.set_property("cpuinfo", "cmake_target_name", "cpuinfo")
        deps.set_property("cudss", "cmake_file_name", "CUDSS")
        deps.set_property("cudss", "cmake_target_name", "torch::cudss")
        deps.set_property("cusparselt", "cmake_file_name", "CUSPARSELT")
        deps.set_property("flatbuffers", "cmake_target_name", "flatbuffers::flatbuffers")
        deps.set_property("fmt", "cmake_target_name", "fmt::fmt-header-only")
        deps.set_property("foxi", "cmake_target_name", "foxi_loader")
        deps.set_property("fp16", "cmake_target_aliases", ["fp16"])
        deps.set_property("gflags", "cmake_target_name", "gflags")
        deps.set_property("gloo", "cmake_file_name", "Gloo")
        deps.set_property("httplib", "cmake_target_name", "httplib")
        deps.set_property("ideep", "cmake_file_name", "MKLDNN")
        deps.set_property("ittapi", "cmake_file_name", "ITT")
        deps.set_property("libbacktrace", "cmake_file_name", "Backtrace")
        deps.set_property("mimalloc", "cmake_target_name", "mimalloc-static")
        deps.set_property("nccl", "cmake_target_name", "__caffe2_nccl")
        deps.set_property("nlohmann_json", "cmake_target_name", "nlohmann")
        deps.set_property("nnpack", "cmake_target_name", "nnpack")
        deps.set_property("psimd", "cmake_target_name", "psimd")
        deps.set_property("tensorpipe", "cmake_target_name", "tensorpipe")
        deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

        # To install pyyaml
        venv = self._utils.PythonVenv(self)
        venv.generate()

    def _regenerate_flatbuffers(self):
        # Re-generate mobile_bytecode_generated.h to allow any flatbuffers version to be used.
        # As of v24.3.25, only updates the flatbuffers version in the generated file.
        self.run(f"flatc --cpp --gen-mutable --no-prefix --scoped-enums mobile_bytecode.fbs",
                 cwd=os.path.join(self.source_folder, "torch/csrc/jit/serialization"))

    def build(self):
        self._utils.pip_install(self, ["pyyaml", "typing-extensions"])
        if self._require_flatbuffers:
            self._regenerate_flatbuffers()
        cmake = CMake(self)
        cmake.configure()
        self._utils.limit_build_jobs(self, gb_mem_per_job=1.5)
        cmake.build(target="torch_cpu")
        if self.options.with_cuda:
            self._utils.limit_build_jobs(self, gb_mem_per_job=5.5)
            cmake.build(target="flash_attention")
            self._utils.limit_build_jobs(self, gb_mem_per_job=1.5)
            cmake.build(target="torch_cuda")
        self._utils.limit_build_jobs(self, gb_mem_per_job=0.5)
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "*", "/home/martin.valgur@milrem.lan/.conan2/p/b/libto868429b30c94d/p", self.package_folder)
        rmdir(self, os.path.join(self.package_folder, "share", "cmake"))
        copy(self, "conan-official-libtorch-vars.cmake",
             self.export_sources_folder,
             os.path.join(self.package_folder, "lib/cmake/Torch"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Torch")

        # Export official CMake variables
        self.cpp_info.builddirs = ["lib/cmake/Torch"]
        self.cpp_info.set_property("cmake_build_modules", ["lib/cmake/Torch/conan-official-libtorch-vars.cmake"])

        def _add_whole_archive_lib(component, libname, shared=False):
            # Reproduces https://github.com/pytorch/pytorch/blob/v2.4.0/cmake/TorchConfig.cmake.in#L27-L43
            if shared:
                self.cpp_info.components[component].libs.append(libname)
            else:
                lib_folder = os.path.join(self.package_folder, "lib")
                if is_apple_os(self):
                    lib_fullpath = os.path.join(lib_folder, f"lib{libname}.a")
                    whole_archive = f"-Wl,-force_load,{lib_fullpath}"
                elif is_msvc(self):
                    lib_fullpath = os.path.join(lib_folder, libname)
                    whole_archive = f"-WHOLEARCHIVE:{lib_fullpath}"
                else:
                    lib_fullpath = os.path.join(lib_folder, f"lib{libname}.a")
                    whole_archive = f"-Wl,--whole-archive,{lib_fullpath},--no-whole-archive"
                self.cpp_info.components[component].exelinkflags.append(whole_archive)
                self.cpp_info.components[component].sharedlinkflags.append(whole_archive)

        self.cpp_info.components["torch"].set_property("cmake_target_name", "torch")
        _add_whole_archive_lib("torch", "torch", shared=self.options.shared)
        self.cpp_info.components["torch"].requires = ["torch_cpu"]
        if self.options.with_cuda:
            self.cpp_info.components["torch"].requires.append("torch_cuda")

        c10 = self.cpp_info.components["c10"]
        c10.set_property("cmake_target_name", "c10")
        c10.libs = ["c10"]
        c10.requires = [
            "concurrentqueue::concurrentqueue",
            "cpp-httplib::cpp-httplib",
            "cpuinfo::cpuinfo",
            "fmt::fmt",
            "libbacktrace::libbacktrace",
            "miniz::miniz",
            "nlohmann_json::nlohmann_json",
        ]
        if self.options.with_gflags:
            c10.requires.append("gflags::gflags")
        if self.options.with_glog:
            c10.requires.append("glog::glog")
        if self.options.with_mimalloc:
            c10.requires.append("mimalloc::mimalloc")
        if self.options.get_safe("with_numa"):
            c10.requires.append("libnuma::libnuma")
        if self.settings.os == "Android":
            c10.system_libs.append("log")

        if self.options.with_cuda:
            c10_cuda = self.cpp_info.components["c10_cuda"]
            c10_cuda.set_property("cmake_target_name", "c10_cuda")
            c10_cuda.libs = ["c10_cuda"]
            c10_cuda.requires = ["c10", "gflags::gflags", "glog::glog", "nvml-stubs::nvml-stubs", "cudart::cudart_"]

            caffe2_nvrtc = self.cpp_info.components["caffe2_nvrtc"]
            caffe2_nvrtc.set_property("cmake_target_name", "caffe2_nvrtc")
            caffe2_nvrtc.libs = ["caffe2_nvrtc"]
            caffe2_nvrtc.requires = ["cudart::cudart_", "nvrtc::nvrtc"]

        torch_cpu = self.cpp_info.components["torch_cpu"]
        torch_cpu.set_property("cmake_target_name", "torch_cpu")
        _add_whole_archive_lib("torch_cpu", "torch_cpu", shared=self.options.shared)
        torch_cpu.includedirs.append("include/torch/csrc/api/include")
        torch_cpu.requires = [
            "c10",
            "eigen::eigen",
            "kineto::kineto",
            "onnx::onnx",
            "pocketfft::pocketfft",
            "protobuf::protobuf",
        ]
        if self._require_sleef:
            torch_cpu.requires.append("sleef::sleef")
        if self._require_flatbuffers:
            torch_cpu.requires.append("flatbuffers::flatbuffers")
        if self.options.with_fbgemm:
            torch_cpu.requires.append("fbgemm::fbgemm")
        if self.options.with_gflags:
            torch_cpu.requires.append("gflags::gflags")
        if self.options.with_glog:
            torch_cpu.requires.append("glog::glog")
        if self.options.with_itt:
            torch_cpu.requires.append("ittapi::ittapi")
        if self.options.with_nnpack:
            torch_cpu.requires.append("nnpack::nnpack")
        if self.options.blas == "generic":
            torch_cpu.requires.append("lapack::lapack")
        if self.options.with_openmp:
            torch_cpu.requires.append("openmp::openmp")
        if self.options.with_opencl:
            torch_cpu.requires.append("opencl-icd-loader::opencl-icd-loader")
        if self.options.with_onednn:
            torch_cpu.requires.append("ideep::ideep")
            if self.options.get_safe("with_acl"):
                torch_cpu.requires.append("arm-compute-library::arm-compute-library")
        if self.options.get_safe("with_vulkan"):
            torch_cpu.requires.append("vulkan-loader::vulkan-loader")
        if self.options.with_xnnpack:
            torch_cpu.requires.append("xnnpack::xnnpack")
        if self.options.get_safe("distributed"):
            if self.options.with_gloo:
                torch_cpu.requires.append("gloo::gloo")
            if self.options.with_mpi:
                torch_cpu.requires.append("openmpi::openmpi")
            if self.options.with_tensorpipe:
                torch_cpu.requires.append("tensorpipe::tensorpipe")
            if self.options.with_ucc:
                torch_cpu.requires.append("ucc::ucc")
        if self.settings.os == "Linux":
            torch_cpu.system_libs.extend(["dl", "m", "pthread", "rt"])

        if self.options.with_cuda:
            torch_cuda = self.cpp_info.components["torch_cuda"]
            torch_cuda.set_property("cmake_target_name", "torch_cuda")
            _add_whole_archive_lib("torch_cuda", "torch_cuda", shared=self.options.shared)
            torch_cuda.requires = [
                "torch_cpu",
                "c10_cuda",
                "cublas::cublas_",
                "cudart::cudart_",
                "cufft::cufft_",
                "curand::curand",
                "cusparse::cusparse",
                "nvml-stubs::nvml-stubs",
                "nvtx::nvtx",
                "cutlass::cutlass",
            ]
            if self.options.with_cudnn:
                torch_cuda.requires.append("cudnn::cudnn")
                torch_cuda.requires.append("cudnn-frontend::cudnn-frontend")
            if not self.options.build_lazy_cuda_linalg:
                torch_cuda.requires.append("cusolver::cusolver_")
            if self.options.with_cusparselt:
                torch_cuda.requires.append("cusparselt::cusparselt")
            if self.options.with_cudss:
                torch_cuda.requires.append("cudss::cudss")
            if self.options.with_cufile:
                torch_cuda.requires.append("cufile::cufile")
            if self.options.with_nvrtc:
                torch_cuda.requires.append("nvrtc::nvrtc")
            if self.options.with_nccl:
                torch_cuda.requires.append("nccl::nccl")
            if self.options.get_safe("distributed"):
                if self.options.with_tensorpipe:
                    torch_cuda.requires.append("tensorpipe::tensorpipe")
                if self.options.with_gloo:
                    torch_cuda.requires.append("gloo::gloo")
                if self.options.with_ucc:
                    torch_cuda.requires.append("ucc::ucc")

        if self.options.get_safe("with_nvshmem"):
            nvshmem_extension = self.cpp_info.components["nvshmem_extension"]
            nvshmem_extension.set_property("cmake_target_name", "nvshmem_extension")
            nvshmem_extension.libs = ["nvshmem_extension"]
            nvshmem_extension.defines = ["USE_NVSHMEM"]
            nvshmem_extension.requires = [
                "nvshmem::nvshmem_host",
                "nvshmem::nvshmem_device",
                "cudart::cudart_",
                "cublas::cublas_",
                "cufft::cufft_",
                "cusparse::cusparse",
            ]
            if self.options.with_cudnn:
                nvshmem_extension.requires.append("cudnn::cudnn")
            self.cpp_info.components["torch_cuda"].requires.append("nvshmem_extension")

        if self.options.shared:
            global_deps = self.cpp_info.components["torch_global_deps"]
            global_deps.libs = ["torch_global_deps"]
            if self.options.with_cuda:
                global_deps.requires.extend(["cudart::cudart_", "nvml-stubs::nvml-stubs"])
            if self.options.get_safe("with_mpi"):
                global_deps.requires.append("openmpi::openmpi")
            # also MKL, if enabled

        if self.options.build_qnnpack:
            self.cpp_info.components["clog"].libs = ["clog"]
            self.cpp_info.components["pytorch_qnnpack"].libs = ["pytorch_qnnpack"]
            self.cpp_info.components["pytorch_qnnpack"].requires = [
                "clog", "cpuinfo::cpuinfo", "fp16::fp16", "fxdiv::fxdiv", "psimd::psimd", "pthreadpool::pthreadpool"
            ]
            self.cpp_info.components["torch_cpu"].requires.append("pytorch_qnnpack")
