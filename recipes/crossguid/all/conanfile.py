import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"

class CrossGUIDConan(ConanFile):
    name = "crossguid"
    description = "Lightweight cross platform C++ GUID/UUID library"
    license = "MIT"
    homepage = "https://github.com/graeme-hill/crossguid"
    topics = ("guid", "uuid")
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
        if not (self.settings.os in ["Windows", "Android"] or is_apple_os(self)):
            self.requires("util-linux-libuuid/[^2.41]")

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.variables["XG_TESTS"] = False
        tc.generate()
        dpes = CMakeDeps(self)
        dpes.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["xg"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        if self.settings.os == "Android":
            self.cpp_info.defines.append("GUID_ANDROID")
        if is_apple_os(self):
            self.cpp_info.frameworks.append("CoreFoundation")
