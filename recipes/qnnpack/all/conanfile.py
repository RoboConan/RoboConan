import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class QnnpackConan(ConanFile):
    name = "qnnpack"
    description = "Quantized Neural Networks PACKage - mobile-optimized library for low-precision high-performance neural network inference"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pytorch/QNNPACK"
    topics = ("neural-networks", "quantization", "mobile", "inference", "simd")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cpuinfo/[>=0.0+git.20231129]")
        self.requires("fp16/[>=0.0+git.20210320]")
        self.requires("fxdiv/[>=0.0+git.20200417]")
        self.requires("pthreadpool/[>=0.0+git.20231129]", transitive_headers=True)
        self.requires("psimd/[>=0.0+git.20200517]")

    def validate(self):
        check_min_cppstd(self, 11)
        if str(self.settings.arch) not in ["x86", "x86_64", "armv7", "armv8"]:
            raise ConanInvalidConfiguration(f"QNNPACK does not support architecture {self.settings.arch}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "CXX_STANDARD 11", "")
        # CMake v4 support
        replace_in_file(self, "deps/clog/CMakeLists.txt",
                        "CMAKE_MINIMUM_REQUIRED(VERSION 3.1 FATAL_ERROR)",
                        "CMAKE_MINIMUM_REQUIRED(VERSION 3.5)")
        # Only install clog for static builds
        replace_in_file(self, "deps/clog/CMakeLists.txt", "INSTALL(TARGETS clog", "message(TRACE ")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["QNNPACK_BUILD_TESTS"] = False
        tc.cache_variables["QNNPACK_BUILD_BENCHMARKS"] = False
        tc.cache_variables["QNNPACK_LIBRARY_TYPE"] = "shared" if self.options.shared else "static"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("clog", "cmake_target_name", "clog")
        deps.set_property("cpuinfo", "cmake_target_name", "cpuinfo")
        deps.set_property("pthreadpool", "cmake_target_name", "pthreadpool")
        deps.set_property("fxdiv", "cmake_target_name", "fxdiv")
        deps.set_property("psimd", "cmake_target_name", "psimd")
        deps.set_property("fp16", "cmake_target_name", "fp16")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["qnnpack"]
        if not self.options.shared:
            self.cpp_info.libs.append("clog")
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]
        elif self.settings.os == "Android":
            self.cpp_info.system_libs = ["m"]
