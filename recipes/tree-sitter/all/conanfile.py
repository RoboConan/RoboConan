import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class TreeSitterConan(ConanFile):
    name = "tree-sitter"
    description = ("Tree-sitter is a parser generator tool and an incremental parsing library. "
                   "It can build a concrete syntax tree for a source file and efficiently update the syntax tree as the source file is edited.")
    license = "MIT"
    homepage = "https://tree-sitter.github.io/tree-sitter"
    topics = ("parser", "incremental", "rust")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "shared": [True, False],
    }
    default_options = {
        "fPIC": True,
        "shared": False,
    }
    languages = ["C"]

    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            self.options.shared.value = False
            self.package_type = "static-library"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "tree-sitter")
        self.cpp_info.libs = ["tree-sitter"]
