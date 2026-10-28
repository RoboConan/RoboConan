import os
import re
import textwrap
from pathlib import Path

from conan import ConanFile
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class UmfConan(ConanFile):
    name = "umf"
    description = "Unified Memory Framework for constructing memory allocators and memory pools"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/oneapi-src/unified-memory-framework"
    topics = ("memory", "allocator", "gpu", "numa", "oneapi")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_jemalloc": [True, False],
        "with_level_zero": [True, False],
        "with_cuda": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_jemalloc": False,
        "with_level_zero": True,
        "with_cuda": False,
    }

    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.get_safe("with_cuda"):
            del self.settings.cuda

    def package_id(self):
        # No device code is built
        if self.info.options.get_safe("with_cuda"):
            del self.info.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("hwloc/[^2.3.0]")
        self.requires("onetbb/[>=2021]")
        if self.options.with_jemalloc:
            self.requires("jemalloc/[^5]")
        if self.options.with_level_zero:
            self.requires("level-zero/[^1]")
        if self.options.get_safe("with_cuda"):
            self.cuda.requires("cuda-driver-stubs")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        # Don't build jemalloc on Linux
        replace_in_file(self, "CMakeLists.txt", "elseif(WINDOWS)", "elseif(TRUE)")
        # Version detection fails without git metadata in the source archive
        replace_in_file(self, "CMakeLists.txt", "set_version_variables()", textwrap.dedent(f"""\
            set(UMF_VERSION "{self.version}")
            set(UMF_CMAKE_VERSION "{self.version}")
            set(UMF_VERSION_PRERELEASE 0)
            set(UMF_VERSION_PRIVATE 0)
            set(UMF_VERSION_BUGFIX 0)
            set(UMF_VERSION_REVISION 0)
        """))
        # Rely on CMakeDeps
        replace_in_file(self, "CMakeLists.txt", "pkg_check_modules(", "# ")
        # Allow unvendored jemalloc to be used
        pool_jemalloc = Path("src/pool/pool_jemalloc.c")
        content = re.sub("je_(?!pool)", "", pool_jemalloc.read_text())
        pool_jemalloc.write_text(content)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["UMF_BUILD_TESTS"] = False
        tc.cache_variables["UMF_BUILD_GPU_TESTS"] = False
        tc.cache_variables["UMF_BUILD_BENCHMARKS"] = False
        tc.cache_variables["UMF_BUILD_BENCHMARKS_MT"] = False
        tc.cache_variables["UMF_BUILD_EXAMPLES"] = False
        tc.cache_variables["UMF_BUILD_GPU_EXAMPLES"] = False
        tc.cache_variables["UMF_BUILD_FUZZTESTS"] = False
        tc.cache_variables["UMF_BUILD_SHARED_LIBRARY"] = self.options.shared
        tc.cache_variables["UMF_BUILD_LEVEL_ZERO_PROVIDER"] = self.options.with_level_zero
        tc.cache_variables["UMF_BUILD_CUDA_PROVIDER"] = bool(self.options.get_safe("with_cuda"))
        tc.cache_variables["UMF_BUILD_LIBUMF_POOL_JEMALLOC"] = self.options.with_jemalloc
        tc.cache_variables["UMF_LINK_HWLOC_STATICALLY"] = False
        tc.cache_variables["UMF_USE_DEBUG_POSTFIX"] = False
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("jemalloc", "cmake_file_name", "JEMALLOC")
        deps.set_property("jemalloc", "cmake_target_name", "jemalloc")
        deps.set_property("hwloc", "cmake_file_name", "LIBHWLOC")
        deps.set_property("hwloc", "cmake_target_name", "hwloc")
        deps.set_property("level-zero", "cmake_file_name", "ZE_LOADER")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.TXT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "licensing"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "umf")

        self.cpp_info.components["umf_headers"].set_property("cmake_target_name", "umf::umf_headers")

        self.cpp_info.components["umf_"].set_property("cmake_target_name", "umf::umf")
        self.cpp_info.components["umf_"].libs = ["umf"]
        if not self.options.shared:
            self.cpp_info.components["umf_"].libs.extend(["umf_ba", "umf_coarse", "umf_utils"])
        self.cpp_info.components["umf_"].requires = ["umf_headers", "hwloc::hwloc", "onetbb::onetbb"]
        if self.options.with_jemalloc:
            self.cpp_info.components["umf_"].requires.append("jemalloc::jemalloc")
        if self.options.with_level_zero:
            self.cpp_info.components["umf_"].requires.append("level-zero::level-zero")
        if self.options.get_safe("with_cuda"):
            self.cpp_info.components["umf_"].requires.append("cuda-driver-stubs::cuda-driver-stubs")
        if not self.options.shared and stdcpp_library(self):
            self.cpp_info.components["umf_"].system_libs.append(stdcpp_library(self))

        if self.options.shared:
            self.cpp_info.components["umf_proxy"].set_property("cmake_target_name", "umf::umf_proxy")
            self.cpp_info.components["umf_proxy"].libs = ["umf_proxy"]
            self.cpp_info.components["umf_proxy"].requires = ["umf_"]
