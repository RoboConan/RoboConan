import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class OpenSpecfunConan(ConanFile):
    name = "openspecfun"
    description = "OpenSpecfun provides a collection of special mathematical functions from the AMOS and Faddeeva libraries."
    license = "MIT"
    homepage = "https://github.com/JuliaMath/openspecfun"
    topics = ("math", "transcendental-functions", "complex-functions")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    provides = ["amos", "faddeeva"]
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.fortran.requires_runtime()

    def validate(self):
        self.fortran.validate_settings()

    def validate_build(self):
        self.fortran.validate_build()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["openspecfun"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
        self.fortran.add_runtime_to_cpp_info(self.cpp_info)
