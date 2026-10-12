import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class OpenAPVConan(ConanFile):
    name = "openapv"
    description = "Open Advanced Professional Video Codec - reference implementation of the APV codec"
    license = "BSD-3-Clause"
    homepage = "https://github.com/AcademySoftwareFoundation/openapv"
    topics = ("video", "codec", "apv", "encoding", "decoding")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],  # For encoder/decoder applications
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported yet")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_TESTS"] = False
        tc.cache_variables["OAPV_BUILD_APPS"] = self.options.tools
        tc.cache_variables["OAPV_BUILD_STATIC_LIB"] = not self.options.shared
        tc.cache_variables["OAPV_BUILD_SHARED_LIB"] = self.options.shared
        tc.cache_variables["OAPV_APP_STATIC_BUILD"] = not self.options.shared
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "oapv")
        self.cpp_info.libs = ["oapv"]
        self.cpp_info.includedirs.append("include/oapv")
        if not self.options.shared:
            self.cpp_info.defines = ["OAPV_STATIC_DEFINE"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]
