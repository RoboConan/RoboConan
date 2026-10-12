import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibZipConan(ConanFile):
    name = "libzip"
    description = "A C library for reading, creating, and modifying zip archives"
    license = "BSD-3-Clause"
    homepage = "https://github.com/nih-at/libzip"
    topics = ("zip", "zip-archives", "zip-editing")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_bzip2": [True, False],
        "with_lzma": [True, False],
        "with_zstd": [True, False],
        "crypto": [False, "win32", "openssl", "mbedtls", "gnutls"],
        "tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_bzip2": True,
        "with_lzma": True,
        "with_zstd": True,
        "crypto": "openssl",
        "tools": True,
    }

    @property
    def _has_zstd_support(self):
        return Version(self.version) >= "1.8.0"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not self._has_zstd_support:
            del self.options.with_zstd
        # Default crypto backend on windows
        if self.settings.os == "Windows":
            self.options.crypto = "win32"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")

        if self.options.with_bzip2:
            self.requires("bzip2/[^1.0.8]")

        if self.options.with_lzma:
            self.requires("xz_utils/[^5.4.5]")

        if self.options.crypto == "openssl":
            self.requires("openssl/[<5]")
        elif self.options.crypto == "mbedtls":
            self.requires("mbedtls/[>=2.28 <4]")
        elif self.options.crypto == "gnutls":
            self.requires("gnutls/[^3.8.2]")

        if self.options.get_safe("with_zstd"):
            self.requires("zstd/[~1.5]")

    def validate(self):
        if self.options.crypto == "win32" and self.settings.os != "Windows":
            raise ConanInvalidConfiguration("Windows is required to use win32 crypto libraries")
        if Version(self.version) >= "1.12" and self.options.crypto == "mbedtls":
            raise ConanInvalidConfiguration("libzip 1.12 and newer no longer support mbedTLS")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TOOLS"] = self.options.tools
        tc.variables["BUILD_REGRESS"] = False
        tc.variables["BUILD_OSSFUZZ"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_DOC"] = False
        tc.variables["ENABLE_COVERAGE"] = False
        tc.variables["LIMIT_LZMA_WINDOW"] = False
        tc.variables["ENABLE_LZMA"] = self.options.with_lzma
        tc.variables["ENABLE_BZIP2"] = self.options.with_bzip2
        if (self.settings.compiler == "gcc"
                and Version(self.settings.compiler.version) >= "14"
                and Version(self.version) < "1.11"):
            # See https://github.com/conan-io/conan-center-index/issues/26034
            # It's an error in gcc >= 14
            # Upstream fixed this silencing this error implicitly from 1.11
            tc.extra_cflags.append("-Wno-incompatible-pointer-types")
        if self._has_zstd_support:
            tc.variables["ENABLE_ZSTD"] = self.options.with_zstd
        tc.variables["ENABLE_COMMONCRYPTO"] = False  # TODO: We need CommonCrypto package
        tc.variables["ENABLE_GNUTLS"] = self.options.crypto == "gnutls"
        if Version(self.version) < "1.12":
            tc.variables["ENABLE_MBEDTLS"] = self.options.crypto == "mbedtls"
        tc.variables["ENABLE_OPENSSL"] = self.options.crypto == "openssl"
        tc.variables["ENABLE_WINDOWS_CRYPTO"] = self.options.crypto == "win32"
        tc.variables["CMAKE_SKIP_INSTALL_RPATH"] = True
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.with_lzma:
            deps.set_property("xz_utils", "cmake_file_name", "LibLZMA")
            deps.set_property("xz_utils", "cmake_target_name", "LibLZMA::LibLZMA")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libzip")
        self.cpp_info.set_property("cmake_target_name", "libzip::zip")
        self.cpp_info.set_property("pkg_config_name", "libzip")

        self.cpp_info.libs = ["zip"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["advapi32"]
            if self.options.crypto == "win32":
                self.cpp_info.system_libs.append("bcrypt")
