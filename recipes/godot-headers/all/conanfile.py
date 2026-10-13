import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class GodotHeadersConan(ConanFile):
    name = "godot-headers"
    description = "C interface headers for Godot extension APIs"
    license = "MIT"
    homepage = "https://github.com/godotengine/godot-headers"
    topics = ("game-engine", "game-development")
    package_type = "header-library"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        pass

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.json", src=self.source_folder, dst=os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
