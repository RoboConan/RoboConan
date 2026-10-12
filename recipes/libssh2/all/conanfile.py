import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class Libssh2Conan(ConanFile):
    name = "libssh2"
    description = "libssh2 is a client-side C library implementing the SSH2 protocol"
    homepage = "https://libssh2.org"
    topics = ("libssh", "ssh", "shell", "ssh2", "connection")
    license = "BSD-3-Clause"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_zlib": [True, False],
        "enable_crypt_none": [True, False],
        "enable_mac_none": [True, False],
        "crypto_backend": ["openssl", "mbedtls"],
        "enable_debug_logging": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_zlib": True,
        "enable_crypt_none": False,
        "enable_mac_none": False,
        "crypto_backend": "openssl",
        "enable_debug_logging": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _mbedtls_cmake_package_name(self):
        pkg_name = "mbedTLS" if Version(self.version) < "1.11.1" else "MbedTLS"
        return pkg_name

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_ZLIB_COMPRESSION"] = self.options.with_zlib
        tc.cache_variables["ENABLE_CRYPT_NONE"] = self.options.enable_crypt_none
        tc.cache_variables["ENABLE_MAC_NONE"] = self.options.enable_mac_none
        tc.cache_variables["ENABLE_DEBUG_LOGGING"] = self.options.enable_debug_logging
        if self.options.crypto_backend == "openssl":
            tc.cache_variables["CRYPTO_BACKEND"] = "OpenSSL"
            tc.cache_variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder.replace("\\", "/")
        elif self.options.crypto_backend == "mbedtls":
            tc.cache_variables["CRYPTO_BACKEND"] = "mbedTLS"
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables['BUILD_TESTING'] = not self.conf.get("tools.build:skip_test", default=True, check_type=bool)
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        # Ensure DLL symbols are exported correctly
        tc.cache_variables["HIDE_SYMBOLS"] = True # sets -DLIBSSH2_EXPORTS
        if Version(self.version) < "1.11" and self.options.shared:
            tc.preprocessor_definitions["LIBSSH2_EXPORTS"] = None
        # To install relocatable shared lib on Macos by default
        tc.variables["CMAKE_POLICY_DEFAULT_CMP0042"] = "NEW"
        if Version(self.version) < "1.11.1":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        # Workaround until github.com/conan-io/conan/pull/12600 is merged
        if is_msvc(self):
            tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("mbedtls", "cmake_file_name", self._mbedtls_cmake_package_name)
        deps.set_property("mbedtls", "cmake_additional_variables_prefixes", ["MBEDTLS"])
        deps.generate()

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # This is a pure C library
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.crypto_backend == "openssl":
            self.requires("openssl/[<5]")
        elif self.options.crypto_backend == "mbedtls":
            if Version(self.version) >= "1.11":
                self.requires("mbedtls/[>=2.28 <4]")
            else:
                self.requires("mbedtls/[^2.28]")

    def build_requirements(self):
        if Version(self.version) >= "1.11":
            self.tool_requires("cmake/[>=3.20 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

        cmakelists = os.path.join("src", "CMakeLists.txt") if Version(self.version) <= "1.10" else "CMakeLists.txt"
        replace_in_file(self, os.path.join(self.source_folder, cmakelists), "MBEDTLS_FOUND", f"{self._mbedtls_cmake_package_name}_FOUND")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "share")) # only docs and manpages
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Libssh2")
        self.cpp_info.set_property("cmake_target_name", "Libssh2::libssh2")
        self.cpp_info.set_property("pkg_config_name", "libssh2")

        self.cpp_info.libs = collect_libs(self)
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("ws2_32")
        elif self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["pthread", "dl"])

        if self.options.shared:
            self.cpp_info.defines.append("LIBSSH2_EXPORTS")
