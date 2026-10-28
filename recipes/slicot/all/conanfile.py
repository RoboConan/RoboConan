import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class SlicotConan(ConanFile):
    name = "slicot"
    description = "SLICOT - Subroutine Library In COntrol Theory"
    license = "BSD-3-Clause"
    homepage = "https://github.com/SLICOT/SLICOT-Reference"
    topics = ("linear-algebra", "control-systems", "system-identification", "eigenvalues","descriptor-systems", "periodic-systems", "control-systems-design")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        self.settings.rm_safe("compiler.cstd")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

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
        self.fortran.add_runtime_to_cpp_info(self.cpp_info)
