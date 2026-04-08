import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class LibyuvConan(ConanFile):
    name = "libyuv"
    homepage = "https://chromium.googlesource.com/libyuv/libyuv/"
    description = "libyuv is an open source project that includes YUV scaling and conversion functionality."
    topics = ["YUV", "libyuv", "google", "chromium"]
    license = "BSD-3-Clause"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_jpeg": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_jpeg": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if is_msvc(self):
            # Only static for msvc
            # Injecting CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS is not sufficient since there are global symbols
            del self.options.shared
            self.package_type = "static-library"
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["TEST"] = False
        tc.cache_variables["LIBYUV_WITH_JPEG"] = bool(self.options.with_jpeg)
        if self.options.get_safe("shared"):
            # Force FPIC for shared, Conan does not set it
            tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["yuv"]
        self.cpp_info.requires = []
        if self.settings.compiler == "msvc":
            self.cpp_info.defines.append("_CRT_SECURE_NO_WARNINGS")
        if self.options.with_jpeg:
            self.cpp_info.requires.append("libjpeg-meta::jpeg")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
