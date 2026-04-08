import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OnnxRuntimeConan(ConanFile):
    name = "onnxruntime"
    description = "ONNX Runtime: cross-platform, high performance ML inferencing and training accelerator"
    license = "MIT AND Apache-2.0 AND MPL-2.0 AND BSD-3-clause"
    homepage = "https://onnxruntime.ai"
    topics = ("deep-learning", "onnx", "neural-networks", "machine-learning", "ai-framework", "hardware-acceleration")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_xnnpack": [True, False],
        "with_cuda": ["full", "minimal", False],
        "cuda_profiling": [True, False],
        "nvtx_profile": [True, False],
        "with_nccl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_xnnpack": False,
        "with_cuda": False,
        "cuda_profiling": False,
        "nvtx_profile": False,
        "with_nccl": False,
        # https://github.com/microsoft/onnxruntime/blob/v1.14.0/cmake/external/onnxruntime_external_deps.cmake#L410
        "onnx/*:disable_static_registration": True,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "cmake/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda
            del self.options.cuda_profiling
            del self.options.nvtx_profile
            del self.options.with_nccl

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # For the official external dependency versions see
        # https://github.com/microsoft/onnxruntime/blob/main/cmake/deps.txt
        absl_max = "<=20240722" if Version(self.version) <= "1.22.2" else ""
        self.requires(f"abseil/[>=20220623.1 {absl_max}]")
        required_onnx_version = self.conan_data["onnx_version_map"][self.version]
        self.requires(f"onnx/[~{required_onnx_version}]")
        self.requires("date/[^3.0]")
        self.requires("re2/[>=20220601]")
        self.requires("flatbuffers/[~23.5]")
        self.requires("boost/[^1.71.0]", headers=True, libs=False)  # for mp11, header only, no need for libraries
        self.requires("safeint/[^3.0.28]")
        self.requires("nlohmann_json/[^3]")
        eigen_version = "[^5.0]" if Version(self.version) >= "1.19.0" else "3.4.0"
        self.requires(f"eigen/{eigen_version}")
        self.requires("ms-gsl/[^4.0.0]")
        self.requires("cpuinfo/[>=0.0+git.20231129]")
        if self.settings.os == "Windows":
            self.requires("wil/[^1.0.240803.1]")
        else:
            self.requires("nsync/[^1.26.0]")
        if self.options.with_xnnpack:
            self.requires("xnnpack/[>=0.0+git.20230715]")
        if self.options.with_cuda:
            # Included in the public onnxruntime/core/providers/cuda/cuda_context.h header
            self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)
            self.requires("cutlass/[^3.9.2]", options={"install_examples_headers": True})
            if self.options.with_cuda == "full":
                self.requires("cudnn-frontend/[^1]")
                self.requires("cudnn/[^9]", transitive_headers=True)
                self.cuda.requires("cublas", transitive_headers=True)
                self.cuda.requires("curand")
                self.cuda.requires("cufft")
            if self.options.cuda_profiling:
                self.cuda.requires("cupti")
            if self.options.nvtx_profile:
                self.requires("nvtx/[^3]")
            if self.options.with_nccl:
                self.requires("nccl/[^2]")

    def validate(self):
        # https://github.com/microsoft/onnxruntime/blob/8f5c79cb63f09ef1302e85081093a3fe4da1bc7d/cmake/CMakeLists.txt#L43-L47
        check_min_cppstd(self, 20 if is_apple_os(self) else 17)
        if not self.dependencies["onnx"].options.disable_static_registration:
            raise ConanInvalidConfiguration("ONNX must be built with `-o onnx/*:disable_static_registration=True`.")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.27 <5]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        copy(self, "onnxruntime_external_deps.cmake",
             src=os.path.join(self.export_sources_folder, "cmake"),
             dst=os.path.join(self.source_folder, "cmake", "external"))
        save(self, "cmake/external/cudnn_frontend.cmake", "")
        # Let Conan manage the C++ standard
        replace_in_file(self, "cmake/CMakeLists.txt", "set(CMAKE_CXX_STANDARD ", "# set(CMAKE_CXX_STANDARD ")
        # Don't try to parse Git info
        replace_in_file(self, "cmake/CMakeLists.txt", "if (Git_FOUND)", "if (0)")
        # Remove an unused cuSPARSE include
        replace_in_file(self, "onnxruntime/core/providers/cuda/cuda_pch.h", "#include <cusparse.h>", "")
        if "1.17" <= Version(self.version) < "1.19":
            # https://github.com/microsoft/onnxruntime/commit/5bfca1dc576720627f3af8f65e25af408271079b
            replace_in_file(self, "cmake/onnxruntime_providers_cuda.cmake",
                            'option(onnxruntime_NVCC_THREADS "Number of threads that NVCC can use for compilation." 1)',
                            'set(onnxruntime_NVCC_THREADS "1" CACHE STRING "Number of threads that NVCC can use for compilation.")')

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["onnxruntime_BUILD_SHARED_LIB"] = self.options.shared
        tc.cache_variables["onnxruntime_BUILD_UNIT_TESTS"] = False
        tc.cache_variables["onnxruntime_ENABLE_CUDA_EP_INTERNAL_TESTS"] = False
        tc.cache_variables["onnxruntime_USE_FULL_PROTOBUF"] = not self.dependencies["protobuf"].options.lite
        tc.cache_variables["onnxruntime_USE_XNNPACK"] = self.options.with_xnnpack
        tc.cache_variables["onnxruntime_USE_CUDA"] = bool(self.options.with_cuda)
        if self.options.with_cuda:
            tc.cache_variables["onnxruntime_CUDA_MINIMAL"] = self.options.with_cuda == "minimal"
            tc.cache_variables["onnxruntime_ENABLE_CUDA_PROFILING"] = self.options.cuda_profiling
            tc.cache_variables["onnxruntime_ENABLE_NVTX_PROFILE"] = self.options.nvtx_profile
            tc.cache_variables["onnxruntime_USE_NCCL"] = self.options.with_nccl
            if self.options.with_cuda == "full":
                tc.variables["CUDNN_MAJOR_VERSION"] = self.dependencies["cudnn"].ref.version.major.value

        # TODO:  https://onnxruntime.ai/docs/execution-providers/
        #  onnxruntime_USE_MIMALLOC
        #  onnxruntime_ENABLE_DLPACK
        #  onnxruntime_ENABLE_TRAINING
        #  onnxruntime_USE_WEBGPU
        #  onnxruntime_USE_COREML
        #  onnxruntime_USE_SNPE
        #  onnxruntime_ENABLE_TRAINING_OPS (MPI)
        #  onnxruntime_USE_MIGRAPHX: migraphx / HIP
        #  onnxruntime_USE_KLEIDIAI
        #  onnxruntime_USE_TENSORRT
        #  onnxruntime_BUILD_WEBASSEMBLY_STATIC_LIB
        #  onnxruntime_USE_DNNL
        #  onnxruntime_USE_VITISAI
        #  onnxruntime_USE_OPENVINO
        #  onnxruntime_USE_QNN

        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True

        # Disable a warning that gets converted to an error
        tc.preprocessor_definitions["_SILENCE_ALL_CXX23_DEPRECATION_WARNINGS"] = "1"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("boost::headers", "cmake_target_name", "Boost::mp11")
        deps.set_property("flatbuffers", "cmake_target_name", "flatbuffers::flatbuffers")
        deps.set_property("cudnn", "cmake_target_name", "CUDNN::cudnn_all")
        deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def build(self):
        cmake = CMake(self)
        # https://github.com/microsoft/onnxruntime/blob/v1.14.1/cmake/CMakeLists.txt#L792
        # onnxruntime builds its targets with COMPILE_WARNING_AS_ERROR ON
        # This will most likely lead to build errors on compilers not undergoing CI testing upstream
        # so disable COMPILE_WARNING_AS_ERROR
        cmake.configure(build_script_folder="cmake", cli_args=["--compile-no-warning-as-error"])
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "onnxruntime")
        self.cpp_info.set_property("cmake_target_name", "onnxruntime::onnxruntime")
        self.cpp_info.set_property("pkg_config_name", "libonnxruntime")

        if self.options.shared:
            self.cpp_info.libs = ["onnxruntime"]
        else:
            onnxruntime_libs = ["session", "optimizer", "providers", "framework", "graph", "util", "mlas", "common", "flatbuffers"]
            if self.options.with_xnnpack:
                onnxruntime_libs.append("providers_xnnpack")
            if self.options.with_cuda:
                onnxruntime_libs.append("providers_cuda")
            self.cpp_info.libs = [f"onnxruntime_{lib}" for lib in onnxruntime_libs]

        if self.options.shared:
            self.cpp_info.includedirs.append("include/onnxruntime")
        else:
            self.cpp_info.includedirs.append("include/onnxruntime/core/session")

        if self.settings.os in ["Linux", "Android", "FreeBSD", "SunOS", "AIX"]:
            self.cpp_info.system_libs.append("m")
        if self.settings.os in ["Linux", "FreeBSD", "SunOS", "AIX"]:
            self.cpp_info.system_libs.append("pthread")
        if is_apple_os(self):
            self.cpp_info.frameworks.append("Foundation")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("shlwapi")
