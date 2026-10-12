import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class GlooConan(ConanFile):
    name = "gloo"
    description = "Collective communications library with various optimized algorithms"
    license = "BSD-3-Clause"
    homepage = "https://github.com/facebookincubator/gloo"
    topics = ("collective-communication", "distributed-training", "machine-learning", "mpi", "cuda", "hpc", "pytorch")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "avx": [True, False],
        "use_torch_dtypes": [True, False],
        "with_ibverbs": [True, False],
        "with_libuv": [True, False],
        "with_mpi": [True, False],
        "with_openssl": [True, False],
        "with_redis": [True, False],
        "with_cuda": [True, False],
        "with_nccl": [True, False],
        "with_rocm": [True, False],
        "with_rccl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "avx": False,
        "use_torch_dtypes": False,
        "with_ibverbs": True,
        "with_libuv": True,
        "with_mpi": True,
        "with_openssl": True,
        "with_redis": True,
        "with_cuda": False,
        "with_nccl": True,
        "with_rocm": False,
        "with_rccl": True,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.with_openssl

    def configure(self):
        if not self.options.with_cuda:
            del self.settings.cuda
            del self.options.with_nccl
        if not self.options.with_rocm:
            del self.options.with_rccl

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_redis:
            self.requires("hiredis/[^1.0]")
        if self.options.with_ibverbs:
            self.requires("rdma-core/[*]")
        if self.options.with_libuv:
            self.requires("libuv/[^1.45.0]")
        if self.options.get_safe("with_openssl"):
            self.requires("openssl/[<5]")
        if self.options.with_mpi:
            self.requires("openmpi/[>=4 <6]")
        if self.options.with_cuda:
            self.cuda.requires("cudart")
            if self.options.with_nccl:
                self.requires("nccl/[^2]")
        # if self.options.with_rocm:
        #     self.requires("rocm/[^5.0]")
        #     if self.options.with_rccl:
        #         self.requires("rccl/[^2.0]")

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.arch not in ["x86_64", "armv8"]:
            raise ConanInvalidConfiguration("Gloo requires a 64-bit architecture")
        if self.options.with_rocm:
            raise ConanInvalidConfiguration("ROCm is not yet supported by this recipe")
        if self.options.with_cuda and self.options.with_rocm:
            raise ConanInvalidConfiguration("CUDA and ROCm support are mutually exclusive")
        if self.options.use_torch_dtypes:
            # Requires libtorch
            raise ConanInvalidConfiguration("The 'use_torch_dtypes' option is not supported yet")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        rm(self, "Find*.cmake", "cmake/Modules")
        # Don't override CUDA architectures
        replace_in_file(self, "cmake/Cuda.cmake", "gloo_select_nvcc_arch_flags(", "# gloo_select_nvcc_arch_flags(")
        # Enable OpenSSL 3.x
        replace_in_file(self, "gloo/CMakeLists.txt", "OpenSSL 1.1", "OpenSSL")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TEST"] = False
        tc.cache_variables["BUILD_BENCHMARK"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["USE_REDIS"] = self.options.with_redis
        tc.cache_variables["USE_IBVERBS"] = self.options.with_ibverbs
        tc.cache_variables["USE_NCCL"] = self.options.get_safe("with_nccl", False)
        tc.cache_variables["USE_RCCL"] = self.options.get_safe("with_rccl", False)
        tc.cache_variables["USE_LIBUV"] = self.options.with_libuv
        tc.cache_variables["USE_TCP_OPENSSL_LINK"] = self.options.get_safe("with_openssl")
        tc.cache_variables["USE_TCP_OPENSSL_LOAD"] = False
        tc.cache_variables["USE_CUDA"] = self.options.with_cuda
        tc.cache_variables["USE_ROCM"] = self.options.with_rocm
        tc.cache_variables["USE_MPI"] = self.options.with_mpi
        tc.cache_variables["USE_AVX"] = self.options.avx
        tc.cache_variables["GLOO_USE_TORCH_DTYPES"] = self.options.use_torch_dtypes
        tc.cache_variables["GLOO_USE_CUDA_TOOLKIT"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("libuv", "cmake_target_name", "uv_a")
        deps.set_property("rdma-core", "cmake_file_name", "ibverbs")
        deps.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))  # CMake config files
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Gloo")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["GLOO"])

        self.cpp_info.components["gloo"].set_property("cmake_target_name", "gloo")
        self.cpp_info.components["gloo"].libs = ["gloo"]
        self.cpp_info.components["gloo"].requires = []
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["gloo"].system_libs = ["pthread"]
        if self.options.with_redis:
            self.cpp_info.components["gloo"].requires.append("hiredis::hiredis")
        if self.options.with_ibverbs:
            self.cpp_info.components["gloo"].requires.append("rdma-core::libibverbs")
        if self.options.with_libuv:
            self.cpp_info.components["gloo"].requires.append("libuv::libuv")
        if self.options.with_openssl:
            self.cpp_info.components["gloo"].requires.append("openssl::openssl")
        if self.options.with_mpi:
            self.cpp_info.components["gloo"].requires.append("openmpi::openmpi")

        if self.options.with_cuda:
            self.cpp_info.components["gloo_cuda"].set_property("cmake_target_name", "gloo_cuda")
            self.cpp_info.components["gloo_cuda"].libs = ["gloo_cuda"]
            self.cpp_info.components["gloo_cuda"].requires = ["gloo", "cudart::cudart_"]
            if self.options.with_nccl:
                self.cpp_info.components["gloo_cuda"].requires.append("nccl::nccl")

        if self.options.with_rocm:
            self.cpp_info.components["gloo_hip"].set_property("cmake_target_name", "gloo_hip")
            self.cpp_info.components["gloo_hip"].libs = ["gloo_hip"]
            self.cpp_info.components["gloo_hip"].requires = ["gloo"]
            if self.options.with_rccl:
                self.cpp_info.components["gloo_hip"].requires.append("rccl::rccl")
