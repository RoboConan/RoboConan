import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class OneDNNOpenVINOConan(ConanFile):
    name = "onednn-openvino"
    description = "A CPU-only fork of oneDNN for the OpenVINO recipe."
    license = "Apache-2.0"
    homepage = "https://github.com/openvinotoolkit/oneDNN"
    topics = ("openvino",)
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cpu_runtime": ["none", "omp", "tbb", "sycl", "threadpool", "seq"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cpu_runtime": "tbb",
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.compiler == "intel-cc" and self.settings.compiler.mode in ["icx", "dpcpp"]:
            # Intel compiler users can take advantage of SYCL support
            self.options.cpu_runtime = "sycl"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.cpu_runtime == "omp":
            self.requires("openmp/system")
        elif self.options.cpu_runtime == "tbb":
            self.requires("onetbb/[>=2021]")
        # Unvendored third-party dependencies
        self.requires("spdlog/[^1.11.0]")
        if self.settings.arch in ["x86", "x86_64", "armv8"]:
            self.requires("ittapi/[^3.23.0]")
        if self.settings.arch in ["x86", "x86_64"]:
            self.requires("xbyak/[^7.21]", transitive_headers=True)
        elif self.settings.arch == "armv8":
            self.requires("xbyak_aarch64/[^1.1.2]", transitive_headers=True)
            self.requires("arm-compute-library/[^52.2.0]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 11)
        if self.options.cpu_runtime == "sycl":
            if self.settings.compiler != "intel-cc" or self.settings.compiler.mode not in ["icx", "dpcpp"]:
                raise ConanInvalidConfiguration("SYCL runtime is only supported with Intel icpx or dpcpp compilers.")

    def source(self):
        info = self.conan_data["sources"][self.version]
        get(self, **info["onednn"], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 2.8.12)",
                        "cmake_minimum_required(VERSION 3.5)")
        rmdir(self, "src/common/ittnotify")
        rmdir(self, "src/common/spdlog")
        rmdir(self, "src/cpu/x64/xbyak")
        rmdir(self, "src/cpu/aarch64/xbyak_aarch64")
        save(self, "src/cpu/aarch64/xbyak_aarch64/CMakeLists.txt", "")
        #Installation of TBBConfig.cmake fails and is not needed anyway
        replace_in_file(self, "src/CMakeLists.txt",
                        'if("${DNNL_CPU_THREADING_RUNTIME}" MATCHES "^(TBB|TBB_AUTO)$")',
                        'if(FALSE)')

    def generate(self):
        # https://github.com/uxlfoundation/oneDNN/blob/v3.8.1/cmake/options.cmake
        # https://github.com/openvinotoolkit/openvino/blob/2025.2.0/src/plugins/intel_cpu/thirdparty/CMakeLists.txt#L36-L59
        tc = CMakeToolchain(self)
        tc.cache_variables["DNNL_LIBRARY_NAME"] = "openvino_onednn_cpu"
        tc.cache_variables["DNNL_LIBRARY_TYPE"] = "SHARED" if self.options.shared else "STATIC"
        tc.cache_variables["DNNL_BUILD_DOC"] = False
        tc.cache_variables["DNNL_BUILD_EXAMPLES"] = False
        tc.cache_variables["DNNL_BUILD_TESTS"] = False
        tc.cache_variables["ONEDNN_BUILD_GRAPH"] = False
        tc.cache_variables["DNNL_ENABLE_WORKLOAD"] = "INFERENCE"
        tc.cache_variables["DNNL_CPU_RUNTIME"] = self.options.cpu_runtime.value.upper()
        tc.cache_variables["DNNL_GPU_RUNTIME"] = "NONE"
        tc.cache_variables["DNNL_BLAS_VENDOR"] = "NONE"
        tc.cache_variables["ONEDNN_ENABLE_GEMM_KERNELS_ISA"] = "SSE41"
        tc.cache_variables["DNNL_ENABLE_PRIMITIVE"] = "CONVOLUTION;DECONVOLUTION;CONCAT;LRN;INNER_PRODUCT;MATMUL;POOLING;REDUCTION;REORDER;RNN;SOFTMAX"
        tc.cache_variables["DNNL_ENABLE_CONCURRENT_EXEC"] = True
        tc.cache_variables["DNNL_ENABLE_PRIMITIVE_CACHE"] = True
        tc.cache_variables["DNNL_ENABLE_MAX_CPU_ISA"] = True
        # ACL is nominally optional, but armv8 compilation fails without it
        tc.cache_variables["DNNL_USE_ACL"] = self.settings.arch == "armv8"
        tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("arm-compute-library", "cmake_file_name", "ACL")
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
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)
        # Install dev headers for OpenVINO onednn extensions
        for subdir in ["common", "cpu"]:
            copy(self, "*.h*",
                 os.path.join(self.source_folder, "src", subdir),
                 os.path.join(self.package_folder, "include", "dnnl_dev", subdir))

    def package_info(self):
        self.cpp_info.set_property("cmake_target_name", "openvino_onednn_cpu")
        self.cpp_info.libs = ["openvino_onednn_cpu"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.cpp_info.includedirs.append(os.path.join("include", "dnnl_dev"))
        if not self.options.shared and stdcpp_library(self):
            self.cpp_info.system_libs.append(stdcpp_library(self))
        if self.options.cpu_runtime == "sycl":
            self.cpp_info.cxxflags.append("-fsycl")
