import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LercConan(ConanFile):
    name = "lerc"
    description = "C++ library for limited Error Raster Compression."
    license = "Apache-2.0"
    homepage = "https://github.com/Esri/lerc"
    topics = ("lerclib", "compression", "decompression", "image", "raster")
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
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 17 if Version(self.version) >= "4.2" else 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        if Version(self.version) >= "3.0":
            rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["LercLib" if Version(self.version) < "4.0.0" else "Lerc"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        if not self.options.shared and stdcpp_library(self):
            self.cpp_info.system_libs.append(stdcpp_library(self))

        if Version(self.version) >= "3.0":
            self.cpp_info.set_property("pkg_config_name", "Lerc")
            if not self.options.shared:
                self.cpp_info.defines = ["LERC_STATIC"]
