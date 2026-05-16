import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class Woff2Conan(ConanFile):
    name = "woff2"
    description = "Encode/decode WOFF2 font format"
    license = "MIT"
    homepage = "https://github.com/google/woff2"
    topics = ("font", "woff2", "compression")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("brotli/[^1.1]", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["NOISY_LOGGING"] = False
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"  # CMake 4 support
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
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.components["woff2common"].set_property("pkg_config_name", "libwoff2common")
        self.cpp_info.components["woff2common"].libs = ["woff2common"]

        self.cpp_info.components["woff2dec"].set_property("pkg_config_name", "libwoff2dec")
        self.cpp_info.components["woff2dec"].libs = ["woff2dec"]
        self.cpp_info.components["woff2dec"].requires = ["woff2common", "brotli::brotlidec"]

        self.cpp_info.components["woff2enc"].set_property("pkg_config_name", "libwoff2enc")
        self.cpp_info.components["woff2enc"].libs = ["woff2enc"]
        self.cpp_info.components["woff2enc"].requires = ["woff2common", "brotli::brotlienc"]
