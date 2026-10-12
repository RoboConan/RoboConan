import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime, is_msvc

required_conan_version = ">=2.4"


class LibGit2Conan(ConanFile):
    name = "libgit2"
    description = (
        "libgit2 is a portable, pure C implementation of the Git core methods "
        "provided as a re-entrant linkable library with a solid API"
    )
    license = "GPL-2.0-linking-exception"
    homepage = "https://libgit2.org/"
    topics = ("git", "scm")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "threadsafe": [True, False],
        "with_iconv": [True, False],
        "with_libssh2": [True, False],
        "with_https": [False, "openssl", "mbedtls", "winhttp", "security"],
        "with_sha1": ["collisiondetection", "commoncrypto", "openssl", "mbedtls", "generic", "win32"],
        "with_ntlmclient": [True, False],
        "with_regex": ["builtin", "pcre", "pcre2", "regcomp_l", "regcomp"],
        "with_http_parser": ["http-parser", "llhttp"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "threadsafe": True,
        "with_iconv": False,
        "with_libssh2": True,
        "with_https": "openssl",
        "with_sha1": "collisiondetection",
        "with_ntlmclient": True,
        "with_regex": "builtin",
        "with_http_parser": "http-parser",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not is_apple_os(self):
            del self.options.with_iconv
        if self.settings.os == "Windows":
            del self.options.with_ntlmclient
        if self.settings.os == "Macos":
            self.options.with_regex = "regcomp_l"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        if self.options.with_http_parser == "http-parser":
            self.requires("http_parser/2.9.4")
        else:
            self.requires("llhttp/[^9.1.3]")
        if self.options.with_libssh2:
            self.requires("libssh2/[^1.11.0]")
        if self._need_openssl:
            self.requires("openssl/[<5]")
        if self._need_mbedtls:
            self.requires("mbedtls/[>=2.28 <4]")
        if self.options.get_safe("with_iconv"):
            self.requires("libiconv/[^1.17]")
        if self.options.with_regex == "pcre":
            self.requires("pcre/[^8.45]")
        elif self.options.with_regex == "pcre2":
            self.requires("pcre2/[^10.42]")

    @property
    def _need_openssl(self):
        return "openssl" in (self.options.with_https, self.options.with_sha1)

    @property
    def _need_mbedtls(self):
        return "mbedtls" in (self.options.with_https, self.options.with_sha1)

    def validate(self):
        if self.options.with_https == "security":
            if not is_apple_os(self):
                raise ConanInvalidConfiguration("security is only valid for Apple products")
        elif self.options.with_https == "winhttp":
            if self.settings.os != "Windows":
                raise ConanInvalidConfiguration("winhttp is only valid on Windows")

        if self.options.with_sha1 == "win32" and self.settings.os != "Windows":
            raise ConanInvalidConfiguration("win32 is only valid on Windows")

        if self.options.with_regex == "regcomp" or self.options.with_regex == "regcomp_l":
            if is_msvc(self):
                raise ConanInvalidConfiguration(f"{self.options.with_regex} isn't supported by Visual Studio")

        if self.settings.os in ["iOS", "tvOS", "watchOS"] and self.options.with_regex == "regcomp_l":
            raise ConanInvalidConfiguration(f"regcomp_l isn't supported on {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["THREADSAFE"] = self.options.threadsafe
        tc.variables["USE_SSH"] = "libssh2" if self.options.with_libssh2 else False
        tc.variables["USE_ICONV"] = self.options.get_safe("with_iconv", False)
        tc.variables["USE_HTTPS"] = {
            "openssl": "OpenSSL",
            "winhttp": "WinHTTP",
            "security": "SecureTransport",
            "mbedtls": "mbedTLS",
            "False": "OFF",
        }[str(self.options.with_https)]
        tc.variables["USE_SHA1"] = {
            "collisiondetection": "CollisionDetection",
            "commoncrypto": "CommonCrypto",
            "openssl": "OpenSSL",
            "mbedtls": "mbedTLS",
            "generic": "Generic",
            "win32": "Win32",
            "False": "OFF",
        }[str(self.options.with_sha1)]
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_CLAR"] = False
        tc.variables["BUILD_CLI"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["USE_HTTP_PARSER"] = self.options.with_http_parser
        tc.variables["REGEX_BACKEND"] = self.options.with_regex
        tc.variables["STATIC_CRT"] = is_msvc_static_runtime(self)
        # REGEX_BACKEND is SET(), avoid options overriding it
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.cache_variables["HAVE_LIBSSH2_MEMORY_CREDENTIALS"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("http_parser", "cmake_file_name", "HTTP_PARSER")
        deps.set_property("libssh2", "cmake_file_name", "LIBSSH2")
        deps.set_property("llhttp", "cmake_file_name", "LLHTTP")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libgit2")
        self.cpp_info.libs = ["git2"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["winhttp", "rpcrt4", "crypt32", "secur32"]
        if self.settings.os in ["Linux", "FreeBSD"] and self.options.threadsafe:
            self.cpp_info.system_libs = ["pthread"]
