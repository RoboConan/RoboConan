import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class QdldlConan(ConanFile):
    name = "qdldl"
    description = "QDLDL: a free LDL factorisation routine for quasi-definite linear systems"
    license = "Apache-2.0"
    homepage = "https://github.com/osqp/qdldl"
    topics = ("linear-algebra", "ldl-factorization", "sparse-matrix")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "float32": [True, False],
        "int32": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "float32": False,
        "int32": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["QDLDL_BUILD_STATIC_LIB"] = not self.options.shared
        tc.cache_variables["QDLDL_BUILD_SHARED_LIB"] = self.options.shared
        tc.cache_variables["QDLDL_FLOAT"] = self.options.float32
        tc.cache_variables["QDLDL_LONG"] = not self.options.int32
        tc.cache_variables["QDLDL_UNITTESTS"] = False
        tc.cache_variables["QDLDL_BUILD_DEMO_EXE"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qdldl")
        self.cpp_info.set_property("cmake_target_name", "qdldl::qdldl")
        self.cpp_info.set_property("cmake_target_aliases", ["qdldl::qdldlstatic"])
        self.cpp_info.libs = ["qdldl"]
        self.cpp_info.includedirs = ["include/qdldl"]
        if self.options.shared:
            self.cpp_info.defines = ["QDLDL_SHARED_LIB"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
