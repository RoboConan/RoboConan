import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class LibmngConan(ConanFile):
    name = "libmng"
    description = "Multiple-image Network Graphics (MNG) reference library"
    license = "DocumentRef-LICENSE:LicenseRef-libmng"  # a slightly reworded libpng license
    homepage = "https://libmng.com/"
    topics = ("mng", "png", "graphics", "image")
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
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        self.requires("lcms/[^2.16]")
        self.requires("libjpeg-meta/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt",
                        "CMAKE_MINIMUM_REQUIRED(VERSION 2.6)",
                        "CMAKE_MINIMUM_REQUIRED(VERSION 3.5)")
        replace_in_file(self, "CMakeLists.txt", '"lib64"', '"lib"')
        replace_in_file(self, "CMakeLists.txt", "${JPEG_LIBRARY}", "JPEG::JPEG")
        replace_in_file(self, "CMakeLists.txt", "${ZLIB_LIBRARY}", "ZLIB::ZLIB")
        replace_in_file(self, "CMakeLists.txt", "${LCMS2_LIBRARY}", "lcms::lcms")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_JPEG"] = True
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_LCMS2"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_MAN"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_GZIP"] = True
        tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("lcms", "cmake_file_name", "LCMS2")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libmng")
        prefix = "lib" if is_msvc(self) else ""
        self.cpp_info.libs = [f"{prefix}mng"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
