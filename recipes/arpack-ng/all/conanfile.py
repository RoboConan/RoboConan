import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class ArpackNgConan(ConanFile):
    name = "arpack-ng"
    description = "ARPACK-NG is a collection of Fortran77 subroutines designed to solve large scale eigenvalue problems"
    license = "BSD-3-Clause"
    homepage = "https://github.com/opencollab/arpack-ng"
    topics = ("eigenvalue", "eigenvector", "sparse-matrix", "linear-algebra", "fortran")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "icb": [True, False],
        "with_eigen": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "icb": True,
        "with_eigen": False,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_eigen:
            self.options.icb.value = True
        if not self.options.icb:
            self.settings.rm_safe("compiler.cppstd")
            self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        if self.options.with_eigen:
            self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        self.fortran.requires_runtime()

    def validate_build(self):
        self.fortran.validate_build()

    def validate(self):
        self.fortran.validate_settings()
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        if mangling != self.fortran.mangling.value:
            raise ConanInvalidConfiguration(
                f"LAPACK uses {mangling}, but the configured Fortran toolchain uses {self.fortran.mangling.value}"
            )
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)
        if self.options.icb:
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["TESTS"] = False
        tc.cache_variables["EXAMPLES"] = False
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["MPI"] = False  # requires Fortran modules for MPI
        tc.cache_variables["ICB"] = self.options.icb
        tc.cache_variables["EIGEN"] = self.options.with_eigen
        tc.cache_variables["PYTHON3"] = False
        tc.cache_variables["INTERFACE64"] = self.dependencies["blas"].options.interface == "ilp64"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "arpackng")
        self.cpp_info.set_property("cmake_target_name", "arpack")
        self.cpp_info.set_property("pkg_config_name", "arpack")
        self.cpp_info.libs = ["arpack"]
        self.cpp_info.includedirs.append("include/arpack")
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs = ["m", "dl"]
        self.fortran.add_runtime_to_cpp_info(self.cpp_info)
