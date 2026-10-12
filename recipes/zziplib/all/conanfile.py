import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class ZziplibConan(ConanFile):
    name = "zziplib"
    description = "The ZZIPlib provides read access on ZIP-archives and unpacked data"
    topics = ("zip", "archive", "decompression")
    homepage = "https://github.com/gdraheim/zziplib"
    license = "GPL-2.0-or-later"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "zzipmapped": [True, False],
        "zzipfseeko": [True, False],
        "zzipwrap": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "zzipmapped": True,
        "zzipfseeko": True,
        "zzipwrap": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")

    def validate(self):
        # Old versions do not support llvm >= 15
        if (Version(self.version) < "0.13.78"
                and self.settings.compiler in ("clang", "apple-clang")
                and Version(self.settings.compiler.version) >= "15.0"):
            raise ConanInvalidConfiguration(f"{self.ref} does not support {self.settings.compiler} >= 15 due to incompatible pointer to integer conversion errors")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        if Version(self.version) < "0.13.80":
            # CMake v4 support
            replace_in_file(self, "CMakeLists.txt", "cmake_minimum_required (VERSION 3.1)", "cmake_minimum_required (VERSION 3.5)")
            replace_in_file(self, "zzip/CMakeLists.txt", "cmake_minimum_required (VERSION 3.1)", "cmake_minimum_required (VERSION 3.5)")
            replace_in_file(self, "zzipwrap/CMakeLists.txt", "cmake_minimum_required (VERSION 3.1)", "cmake_minimum_required (VERSION 3.5)")

    def generate(self):
        tc = CMakeToolchain(self)
        # Older versions had BUILD_STATIC_LIBS option, new ones only have BUILD_SHARED_LIBS
        if Version(self.version) < "0.13.78":
            tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        else:
            # Disable sanitizer for newer versions
            tc.variables["FORTIFY"] = False
        tc.variables["ZZIPCOMPAT"] = self.settings.os != "Windows"
        tc.variables["ZZIPMMAPPED"] = self.options.zzipmapped
        tc.variables["ZZIPFSEEKO"] = self.options.zzipfseeko
        tc.variables["ZZIPWRAP"] = self.options.zzipwrap
        tc.variables["ZZIPSDL"] = False
        tc.variables["ZZIPBINS"] = False
        tc.variables["ZZIPTEST"] = False
        tc.variables["ZZIPDOCS"] = False
        # For msvc shared
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        # Honor BUILD_SHARED_LIBS from conan_toolchain (see https://github.com/conan-io/conan/issues/11840)
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.generate()
        cd = CMakeDeps(self)
        cd.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING.LIB", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zziplib")
        self.cpp_info.set_property("pkg_config_name", "zziplib-all-do-not-use")

        suffix = ""
        if self.settings.build_type == "Release" and \
           (not self.options.shared or self.settings.os == "Windows" or is_apple_os(self)):
            suffix += f"-{Version(self.version).major}"

        # libzzip
        zzip = self.cpp_info.components["zzip"]
        zzip.set_property("cmake_target_name", "zziplib::libzzip")
        zzip.set_property("pkg_config_name", "zziplib")
        zzip.libs = [f"zzip{suffix}"]
        zzip.requires = ["zlib-ng::zlib-ng"]
        # libzzipmmapped
        if self.options.zzipmapped:
            zzipmmapped = self.cpp_info.components["zzipmmapped"]
            zzipmmapped.set_property("cmake_target_name", "zziplib::libzzipmmapped")
            zzipmmapped.set_property("pkg_config_name", "zzipmmapped")
            if Version(self.version) >= "0.13.72" and self.options.shared and is_apple_os(self):
                zzipmmapped.libs = ["zzipmmapped"]
            else:
                zzipmmapped.libs = [f"zzipmmapped{suffix}"]
            zzipmmapped.requires = ["zlib-ng::zlib-ng"]
        # libzzipfseeko
        if self.options.zzipfseeko:
            zzipfseeko = self.cpp_info.components["zzipfseeko"]
            zzipfseeko.set_property("cmake_target_name", "zziplib::libzzipfseeko")
            zzipfseeko.set_property("pkg_config_name", "zzipfseeko")
            if Version(self.version) >= "0.13.72" and self.options.shared and is_apple_os(self):
                zzipfseeko.libs = ["zzipfseeko"]
            else:
                zzipfseeko.libs = [f"zzipfseeko{suffix}"]
            zzipfseeko.requires = ["zlib-ng::zlib-ng"]
        # libzzipwrap
        if self.options.zzipwrap:
            zzipwrap = self.cpp_info.components["zzipwrap"]
            zzipwrap.set_property("cmake_target_name", "zziplib::libzzipwrap")
            zzipwrap.set_property("pkg_config_name", "zzipwrap")
            zzipwrap.libs = [f"zzipwrap{suffix}"]
            zzipwrap.requires = ["zzip", "zlib-ng::zlib-ng"]
