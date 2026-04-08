import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class LibCoapConan(ConanFile):
    name = "libcoap"
    description = "A CoAP (RFC 7252) implementation in C"
    license = "BSD-2-Clause"
    homepage = "https://github.com/obgm/libcoap"
    topics = "coap"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_epoll": [True, False],
        "dtls_backend": [None, "openssl", "gnutls", "tinydtls", "mbedtls"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_epoll": False,
        "dtls_backend": "openssl",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.dtls_backend == "openssl":
            self.requires("openssl/[>=1.1 <4]")
        elif self.options.dtls_backend == "mbedtls":
            self.requires("mbedtls/[>=2.28 <4]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os == "Windows" or is_apple_os(self):
            raise ConanInvalidConfiguration("Platform is currently not supported")

        if self.options.dtls_backend in ["gnutls", "tinydtls"]:
            raise ConanInvalidConfiguration(f"{self.options.dtls_backend} not available yet")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_EPOLL"] = self.options.with_epoll
        tc.variables["ENABLE_DTLS"] = self.options.dtls_backend is not None
        tc.variables["DTLS_BACKEND"] = self.options.dtls_backend
        if self.version != "0.0+git.20200424":
            tc.variables["ENABLE_DOCS"] = False
            tc.variables["ENABLE_EXAMPLES"] = False
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        if self.version == "0.0+git.20200424":
            library_name = "coap"
            cmake_target_name = "coap"
            pkgconfig_filename = "libcoap-2"
        else:
            library_name = "coap-3"
            cmake_target_name = "coap-3"
            pkgconfig_filename = "libcoap-3"

        if self.options.dtls_backend:
            pkgconfig_filename += f"-{self.options.dtls_backend}"

        self.cpp_info.set_property("cmake_file_name", "libcoap")
        self.cpp_info.set_property("cmake_target_name", f"libcoap::{cmake_target_name}")
        if cmake_target_name != "coap":
            # Old target, still provided to not break users
            self.cpp_info.set_property("cmake_target_aliases", ["libcoap::coap"])
        self.cpp_info.set_property("pkg_config_name", pkgconfig_filename)

        self.cpp_info.libs = [library_name]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread"]
            if self.options.dtls_backend == "openssl":
                self.cpp_info.requires = ["openssl::openssl"]
            elif self.options.dtls_backend == "mbedtls":
                self.cpp_info.requires = ["mbedtls::mbedtls"]
