import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class ConanRecipe(ConanFile):
    name = "qpoases"
    description = "qpOASES: an implementation of the Online Active Set Strategy"
    topics = ("quadratic-programming", "optimization", "coin-or")
    homepage = "https://github.com/coin-or/qpOASES"
    license = "LGPL-2.1"
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

    def configure(self):
        # Shared builds on Windows are not supported
        if self.settings.os == "Windows":
            self.options.shared.value = False
            self.package_type = "static-library"
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 2.6)",
                        "cmake_minimum_required(VERSION 3.5)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["QPOASES_BUILD_EXAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qpOASES")
        self.cpp_info.set_property("cmake_target_name", "qpOASES::qpOASES")  # unofficial
        self.cpp_info.libs = ["qpOASES"]
