import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class LibAVIFConan(ConanFile):
    name = "libavif"
    description = "Library for encoding and decoding .avif files"
    license = "BSD-2-Clause"
    homepage = "https://github.com/AOMediaCodec/libavif"
    topics = ("avif",)
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_decoder": ["aom", "dav1d"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_decoder": "dav1d",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libaom-av1/[^3.6.1]")
        self.requires("libyuv/[>=1854]")
        self.requires("libwebp/[^1.3.2]")
        if self.options.with_decoder == "dav1d":
            self.requires("dav1d/[^1.2.1]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["AVIF_ENABLE_WERROR"] = False
        tc.variables["AVIF_BUILD_APPS"] = False
        tc.variables["AVIF_BUILD_EXAMPLES"] = False
        tc.variables["AVIF_BUILD_MAN_PAGES"] = False
        tc.variables["AVIF_BUILD_TESTS"] = False
        tc.variables["AVIF_CODEC_AOM"] = "SYSTEM"
        tc.variables["AVIF_CODEC_AOM_ENCODE"] = True
        tc.variables["AVIF_CODEC_DAV1D"] = "SYSTEM" if self.options.with_decoder == "dav1d" else "OFF"
        tc.variables["AVIF_CODEC_AOM_DECODE"] = self.options.with_decoder == "aom"
        tc.variables["AVIF_CODEC_AVM"] = "OFF"
        tc.variables["AVIF_CODEC_LIBGAV1"] = "OFF"
        tc.variables["AVIF_CODEC_RAV1E"] = "OFF"
        tc.variables["AVIF_CODEC_SVT"] = "OFF"
        tc.variables["AVIF_JPEG"] = "OFF"
        tc.variables["AVIF_LIBSHARPYUV"] = "SYSTEM"
        tc.variables["AVIF_LIBYUV"] = "SYSTEM"
        tc.variables["AVIF_ZLIBPNG"] = "OFF"
        tc.variables["LIBYUV_VERSION"] = str(self.dependencies["libyuv"].ref.version)
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("libaom-av1", "cmake_file_name", "aom")
        deps.set_property("libaom-av1", "cmake_target_name", "aom")
        deps.set_property("libyuv", "cmake_target_name", "yuv::yuv")
        deps.set_property("libwebp", "cmake_file_name", "libsharpyuv")
        deps.set_property("libwebp::sharpyuv", "cmake_target_name", "sharpyuv::sharpyuv")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libavif")
        self.cpp_info.set_property("cmake_target_name", "avif")
        self.cpp_info.set_property("pkg_config_name", "libavif")
        self.cpp_info.libs = ["avif"]
        if self.options.shared:
            self.cpp_info.defines = ["AVIF_DLL"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread", "m"]
            if self.options.with_decoder == "dav1d":
                self.cpp_info.system_libs.append("dl")
        self.cpp_info.requires = ["libyuv::libyuv", "libaom-av1::libaom-av1"]
        if self.options.with_decoder == "dav1d":
            self.cpp_info.requires.append("dav1d::dav1d")
        self.cpp_info.requires.append("libwebp::sharpyuv")
