import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class LibgeotiffConan(ConanFile):
    name = "libgeotiff"
    description = "Libgeotiff is an open source library normally hosted on top " \
                  "of libtiff for reading, and writing GeoTIFF information tags."
    license = "MIT"
    topics = ("geotiff", "tiff")
    homepage = "https://github.com/OSGeo/libgeotiff"
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
        # https://github.com/OSGeo/libgeotiff/blob/1.7.4/libxtiff/xtiffio.h#L10
        self.requires("libtiff/[>=4.5 <5]", transitive_headers=True, transitive_libs=True)
        self.requires("proj/[^9.3.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_DOC"] = False
        tc.variables["BUILD_MAN"] = False
        tc.variables["WITH_UTILITIES"] = False
        tc.variables["WITH_TOWGS84"] = True
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.generate()
        deps = CMakeDeps(self)
        # libgeotiff consumes CMake's FindTIFF target rather than libtiff's config target.
        deps.set_property("libtiff", "cmake_find_mode", "module")
        deps.set_property("libtiff", "cmake_file_name", "TIFF")
        deps.set_property("libtiff::tiff", "cmake_target_name", "TIFF::TIFF")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        fix_apple_shared_install_name(self)
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "doc"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GeoTIFF")
        self.cpp_info.set_property("cmake_target_name", "geotiff_library")
        self.cpp_info.set_property("pkg_config_name", "libgeotiff")

        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.requires = ["libtiff::tiff", "proj::projlib"]
