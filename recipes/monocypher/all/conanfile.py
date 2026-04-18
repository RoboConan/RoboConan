import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class MonocypherConan(ConanFile):
    name = "monocypher"
    description = "An easy to use, easy to deploy crypto library"
    license = "CC0-1.0 OR BSD-2-Clause"
    homepage = "https://monocypher.org"
    topics = "cryptography", "encryption", "signature", "hashing"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "ed25519": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "ed25519": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["MONOCYPHER_VERSION"] = str(self.version)
        tc.cache_variables["MONOCYPHER_ED25519"] = self.options.ed25519
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENCE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "monocypher")
        self.cpp_info.libs = ["monocypher"]
