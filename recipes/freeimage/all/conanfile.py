import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class FreeImageConan(ConanFile):
    name = "freeimage"
    description = "Library for supporting popular image formats such as PNG, BMP, JPEG, TIFF, and others"
    homepage = "https://github.com/danoli3/FreeImage"
    license = "FreeImage OR GPL-3.0-only OR GPL-2.0-only"
    topics = ("image", "decoding", "graphics")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openexr": [True, False],
        "with_webp": [True, False],
        "with_raw": [True, False],
        "with_jxr": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openexr": False,
        "with_webp": True,
        "with_raw": False,
        "with_jxr": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        self.requires("libjpeg-meta/latest")
        self.requires("libpng/[~1.6]")
        self.requires("libtiff/[^4.7.2]")
        self.requires("openjpeg/[^2.5.2]")
        if self.options.with_openexr:
            self.requires("openexr/[^3.5.1]")
            self.requires("imath/[^3.2.0]")
        if self.options.with_webp:
            self.requires("libwebp/[^1.3.2]")
        if self.options.with_raw:
            self.requires("libraw/[>=0.22.2 <1]")
        if self.options.with_jxr:
            self.requires("jxrlib/[*]")

    def validate(self):
        check_min_cppstd(self, 11)

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["FREEIMAGE_STATIC"] = not self.options.shared
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["FREEIMAGE_USE_SYSTEM_LIBS"] = True
        tc.cache_variables["BUILD_ZLIB"] = True
        tc.cache_variables["BUILD_LIBJPEG"] = True
        tc.cache_variables["BUILD_LIBPNG"] = True
        tc.cache_variables["BUILD_LIBTIFF"] = True
        tc.cache_variables["BUILD_LIBOPENJPEG"] = True
        tc.cache_variables["BUILD_OPENEXR"] = self.options.with_openexr
        tc.cache_variables["BUILD_WEBP"] = self.options.with_webp
        tc.cache_variables["BUILD_LIBRAWLITE"] = self.options.with_raw
        tc.cache_variables["BUILD_JXR"] = self.options.with_jxr
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("libtiff", "cmake_file_name", "TIFF")
        deps.set_property("libtiff::tiff", "cmake_target_name", "TIFF::TIFF")
        deps.generate()
        PkgConfigDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "license-*.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "FreeImage")
        self.cpp_info.set_property("cmake_target_name", "FreeImage::FreeImage")
        self.cpp_info.libs = ["FreeImage"]

        self.cpp_info.requires = [
            "zlib-ng::zlib-ng",
            "libjpeg-meta::jpeg",
            "libpng::libpng",
            "libtiff::tiff",
            "openjpeg::openjpeg",
        ]
        if self.options.with_openexr:
            self.cpp_info.requires.extend(["openexr::openexr_openexr", "imath::imath_lib"])
        if self.options.with_webp:
            self.cpp_info.requires.extend(["libwebp::webp", "libwebp::webpdemux", "libwebp::webpmux"])
        if self.options.with_raw:
            self.cpp_info.requires.append("libraw::libraw_")
        if self.options.with_jxr:
            self.cpp_info.requires.append("jxrlib::jxrlib")

        if not self.options.shared:
            self.cpp_info.defines.append("FREEIMAGE_LIB")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("ws2_32")
