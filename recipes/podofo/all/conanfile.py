import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class PodofoConan(ConanFile):
    name = "podofo"
    description = "PoDoFo is a library to work with the PDF file format."
    license = "GPL-2-or-later AND LGPL-2-or-later AND BSD-3-clause"
    homepage = "http://podofo.sourceforge.net"
    topics = ("pdf",)
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "threadsafe": [True, False],
        "with_libidn": [True, False],
        "with_jpeg": [True, False],
        "with_tiff": [True, False],
        "with_png": [True, False],
        "with_unistring": [True, False],
        "with_tools": [True, False],
        "with_lib_only": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "threadsafe": True,
        "with_libidn": True,
        "with_jpeg": True,
        "with_tiff": True,
        "with_png": True,
        "with_unistring": True,
        "with_tools": False,
        "with_lib_only": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

        if is_msvc(self):
            # libunistring recipe raises for Visual Studio
            # TODO: Enable again when fixed?
            self.options.with_unistring = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("freetype/[^2.13.2]")
        self.requires("zlib-ng/[^2.0]")
        self.requires("libxml2/[>=2.12.5 <3]")
        if self.settings.os != "Windows":
            self.requires("fontconfig/[^2.15.0]")
        self.requires("openssl/[>=1.1 <4]")
        if self.options.with_libidn:
            self.requires("libidn/1.36")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.with_tiff:
            self.requires("libtiff/[>=4.5 <5]")
        if self.options.with_png:
            self.requires("libpng/[~1.6]")
        if self.options.with_unistring:
            self.requires("libunistring/[^1]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PODOFO_BUILD_TOOLS"] = self.options.with_tools
        tc.variables["PODOFO_BUILD_LIB_ONLY"] = self.options.with_lib_only
        tc.variables["PODOFO_BUILD_STATIC"] = not self.options.shared
        if not self.options.threadsafe:
            tc.variables["PODOFO_NO_MULTITHREAD"] = True

        # To install relocatable shared lib on Macos
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0042"] = "NEW"

        # Custom CMake options injected in our patch, required to ensure reproducible builds
        tc.variables["PODOFO_WITH_OPENSSL"] = True
        tc.variables["PODOFO_WITH_LIBIDN"] = self.options.with_libidn
        tc.variables["PODOFO_WITH_LIBJPEG"] = self.options.with_jpeg
        tc.variables["PODOFO_WITH_TIFF"] = self.options.with_tiff
        tc.variables["PODOFO_WITH_PNG"] = self.options.with_png
        tc.variables["PODOFO_WITH_UNISTRING"] = self.options.with_unistring

        tc.variables["PODOFO_HAVE_OPENSSL_1_1"] = self.dependencies["openssl"].ref.version >= "1.1"
        openssl = self.dependencies["openssl"]
        tc.variables["PODOFO_HAVE_OPENSSL_NO_RC4"] = not openssl.options.rc4

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libpodofo")

        if not self.options.shared:
            self.cpp_info.libs = ["podofo", "podofo_private"]
            self.cpp_info.defines.append("PODOFO_STATIC")
        else:
            self.cpp_info.libs = ["podofo"]
            self.cpp_info.defines.append("PODOFO_SHARED")

        if self.settings.os in ["Linux", "FreeBSD"] and self.options.threadsafe:
            self.cpp_info.system_libs = ["pthread"]
