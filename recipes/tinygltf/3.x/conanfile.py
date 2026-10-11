import os

from conan import ConanFile
from conan.tools.build import check_min_cstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get

required_conan_version = ">=2.4"


class TinygltfConan(ConanFile):
    name = "tinygltf"
    description = "C11-first glTF 2.0 loader and writer."
    license = "MIT"
    homepage = "https://github.com/syoyo/tinygltf"
    topics = ("gltf", "loader", "writer")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    languages = "C"
    options = {
        "header_only": [True, False],
        "shared": [True, False],
        "fPIC": [True, False],
        "filesystem": [True, False],
    }
    default_options = {
        "header_only": False,
        "shared": False,
        "fPIC": True,
        "filesystem": False,
    }
    implements = ["auto_header_only", "auto_shared_fpic"]

    def export_sources(self):
        copy(self, "conan_build.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        check_min_cstd(self, 11)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_tinygltf_v3_INCLUDE"] = "conan_build.cmake"
        tc.cache_variables["TINYGLTF3_BUILD_TESTS"] = False
        tc.cache_variables["TINYGLTF3_BUILD_LIBRARY"] = not self.options.header_only
        if not self.options.header_only:
            tc.cache_variables["TINYGLTF3_ENABLE_FS"] = self.options.filesystem
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "TinyGLTF")
        self.cpp_info.set_property("cmake_target_name", "tinygltf::tinygltf")
        if self.options.header_only:
            self.cpp_info.bindirs = []
            self.cpp_info.libdirs = []
            self.cpp_info.defines.append("TINYGLTF3_HEADER_ONLY")
            if self.options.filesystem:
                self.cpp_info.defines.append("TINYGLTF3_ENABLE_FS")
        else:
            self.cpp_info.libs = ["tinygltf"]
            if self.settings.os == "Windows" and self.options.shared:
                self.cpp_info.defines.append("TINYGLTF3_API=__declspec(dllimport)")
