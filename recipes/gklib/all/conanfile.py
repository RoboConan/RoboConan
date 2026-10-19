import os
from os import path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class GKlibConan(ConanFile):
    name = "gklib"
    description = "A library of various helper routines and frameworks used by many of the lab's software"
    license = "Apache-2.0"
    homepage = "https://github.com/KarypisLab/GKlib"
    topics = ("karypislab",)
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    @property
    def _is_mingw(self):
        return self.settings.os == "Windows" and self.settings.compiler == "gcc"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.shared
            del self.options.fPIC
            self.package_type = "static-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # For CMake v4 support
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 3.4)",
                        "cmake_minimum_required(VERSION 3.5)")
        # Disable -march=native, which breaks cross-compilation and produces non-portable binaries
        replace_in_file(self, os.path.join(self.source_folder, "GKlibSystem.cmake"),  "-march=native", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ASSERT"] = self.settings.build_type == "Debug"
        tc.variables["ASSERT2"] = self.settings.build_type == "Debug"
        tc.variables["OPENMP"] = self.options.with_openmp
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE.txt", src=self.source_folder,
             dst=path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["GKlib"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        if is_msvc(self) or self._is_mingw:
            self.cpp_info.defines.append("USE_GKREGEX")
        if is_msvc(self):
            self.cpp_info.defines.append("__thread=__declspec(thread)")
