import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime

required_conan_version = ">=2.1"

class TinyEXIFConan(ConanFile):
    name = "tinyexif"
    description = "Tiny ISO-compliant C++ EXIF and XMP parsing library for JPEG"
    license = "MIT"
    homepage = "https://github.com/cdcseacave/TinyEXIF/"
    topics = ("exif", "exif-metadata", "exif-ata-extraction", "exif-reader", "xmp", "xmp-parsing-library")
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

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("tinyxml2/[>=9 <12]")

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LINK_CRT_STATIC_LIBS"] = is_msvc_static_runtime(self)
        tc.variables["BUILD_DEMO"] = False
        tc.variables["BUILD_FUZZER"] = False
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "TinyEXIF")
        self.cpp_info.set_property("cmake_target_name", "TinyEXIF::TinyEXIF")

        suffix = "-2" if self.settings.os == "Windows" and self.options.shared else ""
        self.cpp_info.libs = [f"TinyEXIF{suffix}"]
        if self.options.shared:
            self.cpp_info.defines = ["TINYEXIF_IMPORT"]
