import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class TensorpipeConan(ConanFile):
    name = "tensorpipe"
    description = "A tensor-aware point-to-point communication primitive for machine learning."
    license = "BSD-3-Clause"
    topics = ("tensor", "cuda", "machine-learning", "distributed-computing", "multi-gpu")
    homepage = "https://github.com/pytorch/tensorpipe"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cuda": [True, False],
        "cuda_gdr": [True, False],
        "cuda_ipc": [True, False],
        "ibv": [True, False],
        "shm": [True, False],
        "cma": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cuda": False,
        "cuda_gdr": True,
        "cuda_ipc": True,
        "ibv": True,
        "shm": True,
        "cma": True,
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def config_options(self):
        if self.settings.os != "Linux":
            del self.options.ibv
            del self.options.shm
            del self.options.cma

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.cuda:
            del self.settings.cuda
            del self.options.cuda_ipc

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libnop/0.0+git.20211103")
        self.requires("libuv/[^1.45.0]")
        if self.options.cuda:
            self.cuda.requires("cuda-driver-stubs")
            self.cuda.requires("cudart", transitive_headers=True, libs=False)
            self.cuda.requires("nvml-stubs", libs=False)

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} doesn't support Windows")
        check_min_cppstd(self, 17)
        if self.options.cuda:
            self.cuda.validate_settings()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        replace_in_file(self, "tensorpipe/CMakeLists.txt",
                        "list(APPEND TP_INCLUDE_DIRS $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/third_party/libnop/include>)",
                        "find_package(libnop REQUIRED CONFIG)\n"
                        "list(APPEND TP_INCLUDE_DIRS ${libnop_INCLUDE_DIRS})")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["TP_USE_CUDA"] = self.options.cuda
        tc.cache_variables["TP_ENABLE_IBV"] = self.options.get_safe("ibv", False)
        tc.cache_variables["TP_ENABLE_SHM"] = self.options.get_safe("shm", False)
        tc.cache_variables["TP_ENABLE_CMA"] = self.options.get_safe("cma", False)
        tc.cache_variables["TP_ENABLE_CUDA_IPC"] = self.options.get_safe("cuda_ipc", False)
        tc.cache_variables["TP_ENABLE_CUDA_GDR"] = self.options.get_safe("cuda_gdr", False)
        tc.cache_variables["TP_BUILD_BENCHMARK"] = False
        tc.cache_variables["TP_BUILD_PYTHON"] = False
        tc.cache_variables["TP_BUILD_TESTING"] = False
        tc.cache_variables["TP_BUILD_LIBUV"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("libuv", "cmake_file_name", "uv")
        deps.set_property("libuv", "cmake_target_name", "uv::uv")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Tensorpipe")

        self.cpp_info.components["tensorpipe_"].set_property("cmake_target_name", "tensorpipe")
        self.cpp_info.components["tensorpipe_"].libs = ["tensorpipe"]
        self.cpp_info.components["tensorpipe_"].requires = ["libnop::libnop", "libuv::libuv"]
        if is_apple_os(self):
            self.cpp_info.components["tensorpipe_"].frameworks = ["CoreFoundation", "IOKit"]

        if self.options.cuda:
            self.cpp_info.components["tensorpipe_cuda"].set_property("cmake_target_name", "tensorpipe_cuda")
            self.cpp_info.components["tensorpipe_cuda"].libs = ["tensorpipe_cuda"]
            self.cpp_info.components["tensorpipe_cuda"].requires = [
                "tensorpipe_",
                "cuda-driver-stubs::cuda-driver-stubs",
                "cudart::cudart_",
                "nvml-stubs::nvml-stubs",
            ]
