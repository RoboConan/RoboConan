import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class TrlibConan(ConanFile):
    name = "trlib"
    description = "TRLIB: Trust Region Subproblem Solver Library"
    license = "MIT"
    homepage = "https://github.com/felixlen/trlib"
    topics = ("optimization", "trust-region", "numerical", "linear-algebra")
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

    def requirements(self):
        self.requires("lapack/latest")

    def validate(self):
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 11)
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        if not mangling.startswith("lower_"):
            raise ConanInvalidConfiguration("TRLIB requires BLAS/LAPACK names to be lower_no_underscore, lower_underscore, or lower_underscore_extra")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        save(self, "examples/CMakeLists.txt", "")
        save(self, "tests/CMakeLists.txt", "")
        save(self, "doc/CMakeLists.txt", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        tc.cache_variables["TRLIB_BLAS_LAPACK_UNDERSCORE_SUFFIX"] = not mangling.endswith("no_underscore")
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
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "trlib")
        self.cpp_info.set_property("cmake_target_name", "trlib::trlib")
        self.cpp_info.set_property("pkg_config_name", "trlib")
        self.cpp_info.libs = ["trlib"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
