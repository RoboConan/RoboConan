import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class PopSiftConan(ConanFile):
    name = "popsift"
    description = "PopSift is an open-source implementation of the SIFT algorithm in CUDA."
    license = "MPL-2.0"
    homepage = "https://github.com/alicevision/popsift"
    topics = ("sift", "cuda", "computer-vision", "feature-detection")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.24]")
        self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Don't override the architecture versions set by CudaToolchain
        replace_in_file(self, "CMakeLists.txt",
                        "set(CMAKE_CUDA_ARCHITECTURES",
                        "message(TRACE # set(CMAKE_CUDA_ARCHITECTURES")
        # Let Conan manage static/shared cudart
        replace_in_file(self, "CMakeLists.txt",
                        "set(CMAKE_CUDA_RUNTIME_LIBRARY ",
                        "# set(CMAKE_CUDA_RUNTIME_LIBRARY ")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["PopSift_BUILD_EXAMPLES"] = False
        tc.cache_variables["PopSift_BUILD_DOCS"] = False
        tc.cache_variables["PopSift_USE_TEST_CMD"] = False
        tc.cache_variables["PopSift_USE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        cuda_tc = self.cuda.CudaToolchain()
        cuda_tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PopSift")
        self.cpp_info.set_property("cmake_target_name", "PopSift::popsift")
        self.cpp_info.libs = ["popsift"]
        self.cpp_info.requires = ["cudart::cudart_"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]
