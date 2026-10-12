import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class SlicotConan(ConanFile):
    name = "slicot"
    description = "SLICOT - Subroutine Library In COntrol Theory"
    license = "BSD-3-Clause"
    homepage = "https://github.com/SLICOT/SLICOT-Reference"
    topics = ("linear-algebra", "control-systems", "system-identification", "eigenvalues","descriptor-systems", "periodic-systems", "control-systems-design")
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

    @property
    def _fortran_compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return executables.get("fortran")

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")

    def validate_build(self):
        if not self._fortran_compiler:
            raise ConanInvalidConfiguration(
                "A Fortran compiler is required. "
                "Please add one to `tools.build:compiler_executables={'fortran': '...'}`."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["SLICOT_TESTING"] = False
        tc.cache_variables["SLICOT_INTEGER8"] = self.dependencies["blas"].options.interface == "ilp64"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        ilp64 = self.dependencies["blas"].options.interface == "ilp64"
        self.cpp_info.languages = ["Fortran"]
        self.cpp_info.set_property("cmake_file_name", "SLICOT64" if ilp64 else "SLICOT")
        self.cpp_info.set_property("cmake_target_name", "SLICOT::slicot")
        self.cpp_info.set_property("pkg_config_name", "slicot64" if ilp64 else "slicot")
        self.cpp_info.libs = ["slicot64" if ilp64 else "slicot"]
        self.cpp_info.includedirs = []
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs = ["m", "mvec"]
            if "gfortran" in (self._fortran_compiler or ""):
                self.cpp_info.system_libs.append("gfortran")
