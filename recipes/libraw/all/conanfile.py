import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class LibRawConan(ConanFile):
    name = "libraw"
    description = "LibRaw is a library for reading RAW files obtained from digital photo cameras (CRW/CR2, NEF, RAF, DNG, and others)."
    license = "CDDL-1.0 OR LGPL-2.1-only"
    homepage = "https://www.libraw.org/"
    topics = ("image", "photography", "raw")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_thread_safe": [True, False],
        "with_openmp": [True, False],
        "with_jpeg": [True, False],
        "with_lcms": [True, False],
        "with_zlib": [True, False],

        # Option to override the maximum file size for .CR3 (including .CRM) files.
        # The default limit of 2 GB can be way too small for canon raw movie files (.CRM).
        # Value in bytes.
        "max_cr3_raw_file_size": [None, "ANY"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_thread_safe": False,
        "with_openmp": True,
        "with_jpeg": True,
        "with_lcms": True,
        "with_zlib": True,
        "max_cr3_raw_file_size": None,
    }
    exports_sources = ["CMakeLists.txt"]
    languages = ["C++"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if is_msvc(self):
            del self.options.build_thread_safe

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # TODO: RawSpeed dependency (-DUSE_RAWSPEED)
        # TODO: DNG SDK dependency (-DUSE_DNGSDK)
        if self.options.with_openmp:
            self.requires("openmp/system")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.with_lcms:
            self.requires("lcms/[^2.16]")
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")

    def validate(self):
        check_min_cppstd(self, 11)

        if self.options.get_safe("max_cr3_raw_file_size") and not str(self.options.get_safe("max_cr3_raw_file_size")).isdigit():
            raise ConanInvalidConfiguration("-o='libraw/*:max_cr3_raw_file_size' should be a positive integer")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _library_versions(self):
        version_header = load(self, os.path.join(self.source_folder, "libraw", "libraw_version.h"))
        values = {
            name: int(re.search(rf"#define LIBRAW_SHLIB_{name} +(\d+)", version_header).group(1))
            for name in ("CURRENT", "REVISION", "AGE")
        }
        soversion = values["CURRENT"] - values["AGE"]
        return f"{soversion}.{values['AGE']}.{values['REVISION']}", soversion

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["RAW_LIB_VERSION_STRING"] = self.version
        tc.variables["RAW_LIB_VERSION"], tc.variables["RAW_LIB_SOVERSION"] = self._library_versions
        tc.variables["LIBRAW_SRC_DIR"] = self.source_folder.replace("\\", "/")
        tc.variables["LIBRAW_BUILD_THREAD_SAFE"] = self.options.get_safe("build_thread_safe", False)
        tc.variables["LIBRAW_WITH_OPENMP"] = self.options.with_openmp
        tc.variables["LIBRAW_WITH_JPEG"] = bool(self.options.with_jpeg)
        tc.variables["LIBRAW_WITH_LCMS"] = self.options.with_lcms
        tc.variables["LIBRAW_WITH_ZLIB"] = self.options.with_zlib
        if self.options.get_safe("max_cr3_raw_file_size"):
            tc.variables["LIBRAW_MAX_CR3_RAW_FILE_SIZE"] = self.options.max_cr3_raw_file_size
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="..")
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE*", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, pattern="COPYRIGHT", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.components["libraw_"].set_property("pkg_config_name", "libraw")
        self.cpp_info.components["libraw_"].set_property("cmake_target_name", "libraw::libraw")
        self.cpp_info.components["libraw_"].libs = ["raw"]
        self.cpp_info.components["libraw_"].includedirs.append(os.path.join("include", "libraw"))

        if self.settings.os == "Windows":
            self.cpp_info.components["libraw_"].system_libs.append("ws2_32")
            if not self.options.shared:
                self.cpp_info.components["libraw_"].defines.append("LIBRAW_NODLL")

        requires = []
        if self.options.with_jpeg:
            requires.append("libjpeg-meta::jpeg")
        if self.options.with_lcms:
            requires.append("lcms::lcms")
        if self.options.with_openmp:
            requires.append("openmp::openmp")
        if self.options.with_zlib:
            requires.append("zlib-ng::zlib-ng")
        self.cpp_info.components["libraw_"].requires = requires

        if self.options.get_safe("build_thread_safe"):
            self.cpp_info.components["libraw_r"].set_property("pkg_config_name", "libraw_r")
            self.cpp_info.components["libraw_r"].set_property("cmake_target_name", "libraw::libraw_r")
            self.cpp_info.components["libraw_r"].libs = ["raw_r"]
            self.cpp_info.components["libraw_r"].includedirs.append(os.path.join("include", "libraw"))
            if self.settings.os == "Windows":
                self.cpp_info.components["libraw_r"].system_libs.append("ws2_32")
                if not self.options.shared:
                    self.cpp_info.components["libraw_r"].defines.append("LIBRAW_NODLL")
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["libraw_r"].system_libs.append("pthread")
            self.cpp_info.components["libraw_r"].requires = requires

        if not self.options.shared and stdcpp_library(self):
            self.cpp_info.components["libraw_"].system_libs.append(stdcpp_library(self))
            if self.options.get_safe("build_thread_safe"):
                self.cpp_info.components["libraw_r"].system_libs.append(stdcpp_library(self))
