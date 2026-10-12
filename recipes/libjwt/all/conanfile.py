import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.files import *
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps

required_conan_version = ">=2.1"


class libjwtRecipe(ConanFile):
    name = "libjwt"
    license = "MPL-2.0"
    description = "The C JSON Web Token Library +JWK +JWKS"
    homepage = "https://github.com/benmcollins/libjwt"
    topics = ("json", "jwt", "jwt-token")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_gnutls": [True, False],
        "with_curl": [True, False],
        "with_mbedtls": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_gnutls": False,
        "with_curl": False,
        "with_mbedtls": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/[<5]")
        self.requires("jansson/[^2.14]")
        if self.options.with_gnutls:
            self.requires("gnutls/[^3.8]")
        if self.options.with_curl:
            self.requires("libcurl/[>=7.78 <9]")
        if self.options.with_mbedtls:
            self.requires("mbedtls/[^3.6]")

    def source(self):
        get(self, self.conan_data["sources"][self.version]["url"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["WITH_TESTS"] = False
        tc.cache_variables["WITH_GNUTLS"] = self.options.with_gnutls
        tc.cache_variables["WITH_CURL"] = self.options.with_curl
        tc.cache_variables["WITH_MBEDTLS"] = self.options.with_mbedtls
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
            rm(self, "*.lib", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*.dll", os.path.join(self.package_folder, "bin"))
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))
            rm(self, "*.dylib", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "LibJWT")
        self.cpp_info.set_property("cmake_target_name", "LibJWT::jwt")
        self.cpp_info.set_property("pkg_config_name", "libjwt")
        self.cpp_info.libs = ["jwt"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["dl", "pthread", "rt"]
