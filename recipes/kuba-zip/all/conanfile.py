import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class ZipConan(ConanFile):
    name = "kuba-zip"
    description = "A portable, simple zip library written in C"
    license = "MIT"
    homepage = "https://github.com/kuba--/zip"
    topics = ("zip", "compression", "c", "miniz", "portable", "hacking")

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
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "-Werror", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_DISABLE_TESTING"] = True
        tc.variables["CMAKE_ENABLE_SANITIZERS"] = False
        tc.variables["ZIP_STATIC_PIC"] = self.options.get_safe("fPIC", True)
        tc.variables["ZIP_BUILD_DOCS"] = False
        tc.variables["ZIP_BUILD_FUZZ"] = False
        tc.variables["ZIP_BUILD_TOOLS"] = False
        tc.variables["ZIP_ENABLE_INFLATE"] = True
        tc.variables["ZIP_ENABLE_DEFLATE"] = True
        tc.variables["ZIP_HAVE_SYMLINK"] = True
        tc.variables["MINIZ_NO_STDIO"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        license_file = "LICENSE.txt"
        copy(self, license_file, self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "zip")
        self.cpp_info.set_property("cmake_target_name", "zip::zip")

        self.cpp_info.libs = ["zip"]
        if self.options.shared:
            self.cpp_info.defines.append("ZIP_SHARED")
