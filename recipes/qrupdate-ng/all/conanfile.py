import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class QrupdateNgConan(ConanFile):
    name = "qrupdate-ng"
    description = "Library for fast updates of QR and Cholesky decompositions"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/mpimd-csc/qrupdate-ng"
    topics = ("linear-algebra", "qr-decomposition", "cholesky-decomposition", "fortran")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def config_options(self):
        self.settings.rm_safe("compiler.cstd")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        self.fortran.requires_runtime()

    def validate(self):
        self.fortran.validate_settings()
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        if mangling != self.fortran.mangling.value:
            raise ConanInvalidConfiguration(
                f"LAPACK uses {mangling}, but the configured Fortran toolchain uses {self.fortran.mangling.value}"
            )

    def validate_build(self):
        self.fortran.validate_build()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt",
                        "CMAKE_MINIMUM_REQUIRED(VERSION 3.1.0)",
                        "CMAKE_MINIMUM_REQUIRED(VERSION 3.5)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["INTEGER8"] = self.dependencies["blas"].options.interface == "ilp64"
        tc.cache_variables["ENABLE_TESTING"] = False
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
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qrupdate")
        self.cpp_info.set_property("cmake_target_name", "qrupdate::qrupdate")
        self.cpp_info.set_property("pkg_config_name", "qrupdate")
        self.cpp_info.libs = ["qrupdate"]
        self.cpp_info.includedirs = []
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs = ["m"]
        self.fortran.add_runtime_to_cpp_info(self.cpp_info)
