import os

from conan import ConanFile
from conan.tools.build import stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class HiGHSConan(ConanFile):
    name = "highs"
    description = "high performance serial and parallel solver for large scale sparse linear optimization problems"
    license = "MIT"
    homepage = "https://www.highs.dev/"
    topics = ("simplex", "interior point", "solver", "linear", "programming")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "with_cuda": [True, False],
        "with_hipo": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "with_cuda": False,
        "with_hipo": False,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        if self.options.get_safe("with_hipo"):
            self.requires("blas/latest")
        if self.options.with_cuda:
            self.cuda.requires("cudart")
            self.cuda.requires("cublas")
            self.cuda.requires("cusparse")

    def validate(self):
        if self.options.with_cuda:
            self.cuda.validate_settings()

    def build_requirements(self):
        if self.options.with_cuda:
            self.tool_requires("cmake/[>=3.25]")
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Don't embed the build-time directories in the installed library RPATH
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_CXX_EXE"] = self.options.tools
        tc.variables["CUPDLP_GPU"] = self.options.with_cuda
        tc.variables["HIPO"] = self.options.get_safe("with_hipo", False)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_SHARED_EXTRAS_LIB"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.options.get_safe("with_hipo"):
            for dependency in ("amd", "metis", "rcm"):
                for pattern in ("LICENSE*", "License*"):
                    copy(self, pattern, src=os.path.join(self.source_folder, "extern", dependency),
                         dst=os.path.join(self.package_folder, "licenses", dependency))
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            rm(self, "libhighs_extras.a", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "highs")

        self.cpp_info.components["highs_"].set_property("cmake_target_name", "highs::highs")
        self.cpp_info.components["highs_"].set_property("pkg_config_name", "highs")
        self.cpp_info.components["highs_"].libs = ["highs"]
        if not self.options.shared:
            self.cpp_info.components["highs_"].libs.append("highs_extras")
        self.cpp_info.components["highs_"].includedirs.append("include/highs")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["highs_"].system_libs = ["m", "pthread"]
        if not self.options.shared and stdcpp_library(self):
            self.cpp_info.components["highs_"].system_libs.append(stdcpp_library(self))
        self.cpp_info.components["highs_"].requires = ["zlib-ng::zlib-ng"]
        if self.options.get_safe("with_hipo"):
            self.cpp_info.components["highs_"].requires.append("blas::blas")

        if self.options.with_cuda:
            self.cpp_info.components["cudalin"].set_property("cmake_target_name", "highs::cudalin")
            self.cpp_info.components["cudalin"].set_property("pkg_config_name", "highs_cudalin")
            self.cpp_info.components["cudalin"].libs = ["cudalin"]
            self.cpp_info.components["cudalin"].requires = [
                "cudart::cudart_",
                "cublas::cublas_",
                "cusparse::cusparse",
            ]
            self.cpp_info.components["highs_"].requires.append("cudalin")
