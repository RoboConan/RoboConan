import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class MinizipConan(ConanFile):
    name = "minizip"
    homepage = "https://zlib.net"
    license = "Zlib"
    description = "An experimental package to read and write files in .zip format, written on top of zlib"
    topics = ("zip", "compression", "inflate")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "bzip2": [True, False],
        "tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "bzip2": True,
        "tools": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]", transitive_headers=True)
        if self.options.bzip2:
            self.requires("bzip2/[^1.0.8]", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["MINIZIP_SRC_DIR"] = os.path.join(self.source_folder, "contrib", "minizip").replace("\\", "/")
        tc.variables["MINIZIP_ENABLE_BZIP2"] = self.options.bzip2
        tc.variables["MINIZIP_BUILD_TOOLS"] = self.options.tools
        # fopen64 and similar are unavailable before API level 24: https://github.com/madler/zlib/pull/436
        if self.settings.os == "Android" and int(str(self.settings.os.api_level)) < 24:
            tc.preprocessor_definitions["IOAPI_NO_64"] = "1"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="..")
        cmake.build()

    def _extract_license(self):
        zlib_h = load(self, os.path.join(self.source_folder, "zlib.h"))
        return zlib_h[2:zlib_h.find("*/", 1)]

    def package(self):
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), self._extract_license())
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["minizip"]
        self.cpp_info.includedirs.append(os.path.join("include", "minizip"))
        self.cpp_info.requires.append("zlib-ng::zlib-ng")
        if self.options.bzip2:
            self.cpp_info.defines.append("HAVE_BZIP2")
            self.cpp_info.requires.append("bzip2::bzip2")
