import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OpenEXRConan(ConanFile):
    name = "openexr"
    description = "OpenEXR is a high dynamic-range (HDR) image file format developed by Industrial Light & " \
                  "Magic for use in computer imaging applications."
    license = "BSD-3-Clause"
    homepage = "https://github.com/AcademySoftwareFoundation/openexr"
    topics = ("openexr", "hdr", "image", "picture")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "threading": [True, False],
        "with_tbb": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "threading": True,
        "with_tbb": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Note: OpenEXR and Imath are versioned independently.
        # https://github.com/AcademySoftwareFoundation/openexr/blob/v3.5.2/src/lib/OpenEXR/ImfRgba.h#L18
        self.requires("imath/[^3.1.9]", transitive_headers=True)
        self.requires("libdeflate/[^1.19]")
        self.requires("openjph/[>=0.32 <1]")
        self.requires("zstd/[^1.5.0]")
        if self.options.with_tbb:
            self.requires("onetbb/[>=2021.13 <2024]")

    def configure(self):
        if self.options.with_tbb:
            self.options.threading.value = True

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Even without BUILD_WEBSITE, Website targets are compiled with the libraries.
        save(self, "website/src/CMakeLists.txt", "")
        rmdir(self, "external/OpenJPH")
        rmdir(self, "external/deflate")
        rmdir(self, "external/zstd")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["OPENEXR_INSTALL"] = True
        tc.variables["OPENEXR_BUILD_LIBS"] = True
        tc.variables["OPENEXR_ENABLE_THREADING"] = self.options.threading
        tc.variables["OPENEXR_USE_TBB"] = self.options.with_tbb
        tc.variables["OPENEXR_BUILD_TOOLS"] = False
        tc.variables["OPENEXR_INSTALL_TOOLS"] = False
        tc.variables["OPENEXR_INSTALL_DEVELOPER_TOOLS"] = False
        tc.variables["OPENEXR_BUILD_EXAMPLES"] = False
        tc.variables["OPENEXR_BUILD_PYTHON"] = False
        tc.variables["OPENEXR_BUILD_OSS_FUZZ"] = False
        tc.variables["OPENEXR_TEST_LIBRARIES"] = False
        tc.variables["OPENEXR_TEST_TOOLS"] = False
        tc.variables["OPENEXR_TEST_PYTHON"] = False
        tc.variables["OPENEXR_USE_CLANG_TIDY"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_WEBSITE"] = False
        tc.variables["OPENEXR_INSTALL_DOCS"] = False
        tc.variables["OPENEXR_INSTALL_PKG_CONFIG"] = False
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_Imath"] = True
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_libdeflate"] = True
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_openjph"] = True
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_zstd"] = True
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def _add_component(self, name):
        component = self.cpp_info.components[name.lower()]
        component.set_property("cmake_target_name", f"OpenEXR::{name}")
        return component

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenEXR")
        self.cpp_info.set_property("pkg_config_name", "OpenEXR")

        lib_suffix = ""
        if not self.options.shared or self.settings.os == "Windows":
            v = Version(self.version)
            lib_suffix += f"-{v.major}_{v.minor}"
        if self.settings.build_type == "Debug":
            lib_suffix += "_d"

        # OpenEXR::OpenEXRConfig
        OpenEXRConfig = self._add_component("OpenEXRConfig")
        OpenEXRConfig.includedirs.append("include/OpenEXR")

        # OpenEXR::IexConfig
        IexConfig = self._add_component("IexConfig")
        IexConfig.includedirs = OpenEXRConfig.includedirs

        # OpenEXR::IlmThreadConfig
        IlmThreadConfig = self._add_component("IlmThreadConfig")
        IlmThreadConfig.includedirs = OpenEXRConfig.includedirs

        # OpenEXR::Iex
        Iex = self._add_component("Iex")
        Iex.libs = [f"Iex{lib_suffix}"]
        Iex.requires = ["openexrconfig"]
        if self.settings.os == "Linux":
            Iex.system_libs = ["dl"]

        # OpenEXR::IlmThread
        IlmThread = self._add_component("IlmThread")
        IlmThread.libs = [f"IlmThread{lib_suffix}"]
        IlmThread.requires = ["openexrconfig", "iex"]
        if self.options.threading and self.settings.os in ["Linux", "FreeBSD"]:
            IlmThread.system_libs = ["pthread"]
        if self.options.with_tbb:
            IlmThread.requires.append("onetbb::libtbb")
        if self.settings.os == "Linux":
            IlmThread.system_libs.append("dl")

        # OpenEXR::OpenEXRCore
        OpenEXRCore = self._add_component("OpenEXRCore")
        OpenEXRCore.libs = [f"OpenEXRCore{lib_suffix}"]
        OpenEXRCore.requires = [
            "openexrconfig", "imath::imath",
            "libdeflate::libdeflate", "openjph::openjph", "zstd::zstd",
        ]
        if self.settings.os == "Linux":
            OpenEXRCore.system_libs.append("dl")

        # OpenEXR::OpenEXR
        OpenEXR = self._add_component("OpenEXR")
        OpenEXR.libs = [f"OpenEXR{lib_suffix}"]
        OpenEXR.requires = [
            "openexrcore",
            "ilmthread",
            "iex",
            "openexrconfig",
            "imath::imath",
        ]
        if self.settings.os == "Linux":
            OpenEXR.system_libs = ["dl"]

        # OpenEXR::OpenEXRUtil
        OpenEXRUtil = self._add_component("OpenEXRUtil")
        OpenEXRUtil.libs = [f"OpenEXRUtil{lib_suffix}"]
        OpenEXRUtil.requires = ["openexrconfig", "openexr", "openexrcore"]
        if self.settings.os == "Linux":
            OpenEXRUtil.system_libs = ["dl"]

        if self.settings.os == "Windows" and self.options.shared:
            for component in (Iex, IlmThread, OpenEXRCore, OpenEXR, OpenEXRUtil):
                component.defines.append("OPENEXR_DLL")
