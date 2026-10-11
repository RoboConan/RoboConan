import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd, valid_min_cppstd
from conan.tools.cmake import cmake_layout, CMakeToolchain, CMakeDeps, CMake
from conan.tools.files import *

required_conan_version = ">=2.1"


class TinygltfConan(ConanFile):
    name = "tinygltf"
    description = "Header only C++11 tiny glTF 2.0 library."
    license = "MIT"
    homepage = "https://github.com/syoyo/tinygltf"
    topics = ("gltf", "header-only")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "header_only": [True, False],
        "shared": [True, False],
        "fPIC": [True, False],
        "draco": [True, False],
        "json": ["nlohmann", "rapidjson"],
        "stb_image": [True, False],
        "stb_image_write": [True, False],
    }
    default_options = {
        "header_only": False,
        "shared": False,
        "fPIC": True,
        "draco": False,
        "json": "nlohmann",
        "stb_image": True,
        "stb_image_write": True,
    }
    implements = ["auto_header_only", "auto_shared_fpic"]

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.json == "nlohmann":
            self.requires("nlohmann_json/[^3]", transitive_headers=True)
        elif self.options.json == "rapidjson":
            self.requires("rapidjson/[*]", transitive_headers=True)
        if self.options.draco:
            self.requires("draco/[^1.5.6]", transitive_headers=True)
        if self.options.stb_image or self.options.stb_image_write:
            self.requires("stb/[*]", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 11)", "")
        replace_in_file(self, "tiny_gltf.h", '#include "json.hpp"', "#include <nlohmann/json.hpp>")
        for include in ["document.h", "prettywriter.h", "rapidjson.h", "stringbuffer.h", "writer.h"]:
            replace_in_file(self, "tiny_gltf.h", f'#include "{include}"', f'#include <rapidjson/{include}>')
        for include in ["stb_image.h", "stb_image_write.h"]:
            replace_in_file(self, "tiny_gltf.h", f'#include "{include}"', f'#include <{include}>')

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_tinygltf_INCLUDE"] = "conan_deps.cmake"
        tc.cache_variables["TINYGLTF_HEADER_ONLY"] = self.options.header_only
        tc.cache_variables["TINYGLTF_INSTALL_VENDOR"] = False
        tc.cache_variables["TINYGLTF_BUILD_LOADER_EXAMPLE"] = False
        tc.cache_variables["WITH_NLOHMANN_JSON"] = self.options.json == "nlohmann"
        tc.cache_variables["WITH_RAPIDJSON"] = self.options.json == "rapidjson"
        tc.cache_variables["WITH_DRACO"] = self.options.draco
        tc.cache_variables["WITH_STB_IMAGE"] = self.options.stb_image
        tc.cache_variables["WITH_STB_IMAGE_WRITE"] = self.options.stb_image_write
        if valid_min_cppstd(self, 14):
            tc.preprocessor_definitions["TINYGLTF_USE_CPP14"] = None
        tc.generate()
        deps = CMakeDeps(self)
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

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "TinyGLTF")
        self.cpp_info.set_property("cmake_target_name", "tinygltf::tinygltf")
        if self.options.header_only:
            self.cpp_info.bindirs = []
            self.cpp_info.libdirs = []
            # unofficial
            self.cpp_info.defines.append("TINYGLTF_HEADER_ONLY")
        else:
            self.cpp_info.libs = ["tinygltf"]
        if self.options.draco:
            self.cpp_info.defines.append("TINYGLTF_ENABLE_DRACO")
        if self.options.json == "rapidjson":
            self.cpp_info.defines.append("TINYGLTF_USE_RAPIDJSON")
        if not self.options.stb_image:
            self.cpp_info.defines.append("TINYGLTF_NO_STB_IMAGE")
        if not self.options.stb_image_write:
            self.cpp_info.defines.append("TINYGLTF_NO_STB_IMAGE_WRITE")
        if valid_min_cppstd(self, 14):
            self.cpp_info.defines.append("TINYGLTF_USE_CPP14")
