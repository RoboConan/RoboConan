import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibheifConan(ConanFile):
    name = "libheif"
    description = "libheif is an HEIF and AVIF file format decoder and encoder."
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    topics = ("heif", "codec", "video")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libde265": [True, False],
        "with_x265": [True, False],
        "with_libaomav1": [True, False],
        "with_dav1d": [True, False],
        "with_jpeg": [True, False],
        "with_openjpeg": [True, False],
        "with_openjph": [True, False],
        "with_openh264": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libde265": True,
        "with_x265": False,
        "with_libaomav1": False,
        "with_dav1d": False,
        "with_jpeg": False,
        "with_openjpeg": False,
        "with_openjph": False,
        "with_openh264": False,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_libde265:
            self.requires("libde265/[^1.0.12]")
        if self.options.with_x265:
            self.requires("libx265/[>=3.4 <5]")
        if self.options.with_libaomav1:
            self.requires("libaom-av1/[^3.6.1]")
        if self.options.with_dav1d:
            self.requires("dav1d/[^1.2.1]")
        if self.options.get_safe("with_jpeg"):
            self.requires("libjpeg-meta/latest")
        if self.options.get_safe("with_openjpeg"):
            self.requires("openjpeg/[^2.5.2]")
        if self.options.get_safe("with_openjph"):
            self.requires("openjph/[>=0.32 <1]")
        if self.options.get_safe("with_openh264"):
            self.requires("openh264/[^2.4.1]")

    def validate_build(self):
        if Version(self.version) >= "1.19.0":
            check_min_cppstd(self, "20")

    def validate(self):
        check_min_cppstd(self, "11")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "set(CMAKE_POSITION_INDEPENDENT_CODE", "#set(CMAKE_POSITION_INDEPENDENT_CODE")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_PLUGIN_LOADING"] = False
        tc.cache_variables["WITH_LIBSHARPYUV"] = False
        tc.cache_variables["WITH_LIBDE265"] = self.options.with_libde265
        tc.cache_variables["WITH_LIBDE265_PLUGIN"] = False
        tc.cache_variables["WITH_X265"] = self.options.with_x265
        tc.cache_variables["WITH_X265_PLUGIN"] = False
        tc.cache_variables["WITH_KVAZAAR"] = False
        tc.cache_variables["WITH_UVG266"] = False
        tc.cache_variables["WITH_VVDEC"] = False
        tc.cache_variables["WITH_VVENC"] = False
        tc.cache_variables["WITH_X264"] = False
        tc.cache_variables["WITH_OpenH264_DECODER"] = self.options.get_safe("with_openh264", False)
        tc.cache_variables["WITH_OpenH264_DECODER_PLUGIN"] = False
        tc.cache_variables["WITH_AOM_DECODER"] = self.options.with_libaomav1
        tc.cache_variables["WITH_AOM_ENCODER"] = self.options.with_libaomav1
        tc.cache_variables["WITH_AOM_DECODER_PLUGIN"] = False
        tc.cache_variables["WITH_AOM_ENCODER_PLUGIN"] = False
        tc.cache_variables["WITH_RAV1E"] = False
        tc.cache_variables["WITH_SvtEnc"] = False
        tc.cache_variables["WITH_DAV1D"] = self.options.with_dav1d
        tc.cache_variables["WITH_DAV1D_PLUGIN"] = False
        tc.cache_variables["WITH_FFMPEG_DECODER"] = False
        tc.cache_variables["WITH_UNCOMPRESSED_CODEC"] = False
        tc.cache_variables["WITH_WEBCODECS"] = False
        tc.cache_variables["WITH_EXAMPLES"] = False
        tc.cache_variables["WITH_EXAMPLE_HEIF_THUMB"] = False
        tc.cache_variables["WITH_EXAMPLE_HEIF_VIEW"] = False
        tc.cache_variables["WITH_GDK_PIXBUF"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_DEVELOPMENT_TOOLS"] = False
        tc.cache_variables["BUILD_DOCUMENTATION"] = False
        tc.cache_variables["WITH_FUZZERS"] = False
        tc.cache_variables["WITH_HEADER_COMPRESSION"] = False
        tc.cache_variables["WITH_JPEG_DECODER"] = self.options.get_safe("with_jpeg", False)
        tc.cache_variables["WITH_JPEG_ENCODER"] = self.options.get_safe("with_jpeg", False)
        tc.cache_variables["WITH_JPEG_DECODER_PLUGIN"] = False
        tc.cache_variables["WITH_JPEG_ENCODER_PLUGIN"] = False
        tc.cache_variables["WITH_OpenJPEG_DECODER"] = self.options.get_safe("with_openjpeg", False)
        tc.cache_variables["WITH_OpenJPEG_ENCODER"] = self.options.get_safe("with_openjpeg", False)
        tc.cache_variables["WITH_OpenJPEG_DECODER_PLUGIN"] = False
        tc.cache_variables["WITH_OpenJPEG_ENCODER_PLUGIN"] = False
        tc.cache_variables["WITH_OPENJPH_ENCODER"] = self.options.get_safe("with_openjph", False)
        tc.cache_variables["WITH_OPENJPH_ENCODER_PLUGIN"] = False
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        tc.cache_variables["CMAKE_COMPILE_WARNING_AS_ERROR"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("dav1d", "cmake_additional_variables_prefixes", ["DAV1D"])
        deps.set_property("libde265", "cmake_file_name", "LIBDE265")
        deps.set_property("openjph", "cmake_additional_variables_prefixes", ["OPENJPH"])
        if Version(self.version) >= "1.19.0":
            deps.set_property("openh264", "cmake_file_name", "OpenH264")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "heif")
        self.cpp_info.set_property("pkg_config_name", "libheif")
        self.cpp_info.libs = ["heif"]
        if self.options.with_libde265:
            self.cpp_info.requires.append("libde265::libde265")
        if self.options.with_x265:
            self.cpp_info.requires.append("libx265::libx265")
        if self.options.with_libaomav1:
            self.cpp_info.requires.append("libaom-av1::libaom-av1")
        if self.options.with_dav1d:
            self.cpp_info.requires.append("dav1d::dav1d")
        if self.options.get_safe("with_jpeg"):
            self.cpp_info.requires.append("libjpeg-meta::jpeg")
        if self.options.get_safe("with_openjpeg"):
            self.cpp_info.requires.append("openjpeg::openjpeg")
        if self.options.get_safe("with_openjph"):
            self.cpp_info.requires.append("openjph::openjph")
        if self.options.get_safe("with_openh264"):
            self.cpp_info.requires.append("openh264::openh264")
        if not self.options.shared:
            self.cpp_info.defines = ["LIBHEIF_STATIC_BUILD"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        if not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.system_libs.append(libcxx)
