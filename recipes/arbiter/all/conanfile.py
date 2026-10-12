import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class PackageConan(ConanFile):
    name = "arbiter"
    description = "Uniform access to the filesystem, HTTP, S3, GCS, Dropbox, etc."
    license = "MIT"
    homepage = "https://github.com/connormanning/arbiter"
    topics = ("filesystem", "http", "s3", "gcs", "dropbox")

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
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libcurl/[>=7.78.0 <9]")
        self.requires("openssl/[<5]")
        self.requires("zlib-ng/[^2.0]")
        self.requires("nlohmann_json/[^3]", transitive_headers=True)
        self.requires("rapidxml/1.13", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def _patch_sources(self):
        # Unvendor nlohmann_json
        rmdir(self, os.path.join(self.source_folder, "arbiter", "third", "json"))
        save(self, os.path.join(self.source_folder, "arbiter", "third", "json", "json.hpp"),
             "#include <nlohmann/json.hpp>\n")
        # Unvendor rapidxml
        rmdir(self, os.path.join(self.source_folder, "arbiter", "third", "xml"))
        save(self, os.path.join(self.source_folder, "arbiter", "third", "xml", "xml.hpp"),
             "#include <rapidxml/rapidxml.hpp>\n"
             "namespace Xml = rapidxml;\n")


    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder="..")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "*.hpp",
             os.path.join(self.source_folder, "arbiter"),
             os.path.join(self.package_folder, "include", "arbiter"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["arbiter"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("pthread")
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs.append("shlwapi")
        if self.options.shared:
            self.cpp_info.defines.append("ARBITER_DLL_IMPORT")
