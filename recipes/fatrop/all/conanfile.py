import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class FatropConan(ConanFile):
    name = "fatrop"
    description = ("Fatrop is a nonlinear optimal control problem solver that aims to be fast, "
                   "support a broad class of optimal control problems and achieve a high numerical robustness.")
    license = "LGPL-3.0"
    homepage = "https://github.com/meco-group/fatrop"
    topics = ("optimization", "optimal-control", "interior-point", "nonlinear-optimization")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_legacy": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_legacy": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("blasfeo/[>=0.1 <1]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.compiler == "msvc":
            # MSVC is currently not supported: https://github.com/meco-group/fatrop/issues/11
            # Fails with many template errors.
            raise ConanInvalidConfiguration("MSVC is not supported")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_POSITION_INDEPENDENT_CODE ON)", "")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        replace_in_file(self, "CMakeLists.txt", "-march=native", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["WITH_BUILD_BLASFEO"] = False
        tc.cache_variables["BUILD_WITH_LEGACY"] = self.options.enable_legacy
        tc.preprocessor_definitions["NOMINMAX"] = None
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fatrop")
        self.cpp_info.set_property("cmake_target_name", "fatrop::fatrop")
        self.cpp_info.libs = ["fatrop"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
