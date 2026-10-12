import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

class LaceModelicaConan(ConanFile):
    name = "lacemodelica"
    description = "BaseModelica parser and compiler with FMU and ONNX output"
    license = "MIT"
    homepage = "https://github.com/yacoda/lacemodelica"
    topics = ("modelica", "parser", "fmu", "onnx")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("antlr4-cppruntime/[^4]")
        self.requires("tinyxml2/[>=10 <12]")
        self.requires("onnx/[^1]")
        self.requires("protobuf/[>=3.21.12 <8]")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["LACEMODELICA_BUILD_EXE"] = self.options.tools
        tc.cache_variables["REGENERATE_PARSER"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("tinyxml2", "cmake_target_name", "tinyxml2")
        deps.set_property("protobuf", "cmake_file_name", "Protobuf")
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
        self.cpp_info.set_property("cmake_file_name", "LACEMODELICA")
        self.cpp_info.set_property("cmake_target_name", "lacemodelica::lacemodelica")
        self.cpp_info.libs = ["lacemodelica"]
        if not self.options.shared:
            self.cpp_info.defines.append("LACEMODELICA_STATIC")
        self.cpp_info.bindirs = ["bin"] if self.options.tools else []
