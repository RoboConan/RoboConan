import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class LbfgsbConan(ConanFile):
    name = "lbfgsb"
    description = "L-BFGS-B is a limited-memory quasi-Newton code for bound-constrained optimization."
    license = "BSD-3-Clause"
    homepage = "https://users.iems.northwestern.edu/~nocedal/lbfgsb.html"
    topics = ("optimization", "quasi-newton", "bound-constrained")
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
        # Fortran library, not C or C++
        self.settings.rm_safe("compiler.cstd")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.fortran.requires_runtime()

    def validate(self):
        self.fortran.validate_settings()

    def validate_build(self):
        self.fortran.validate_build()

    def source(self):
        get(self, **self.conan_data["sources"][self.version])
        move_folder_contents(self, os.path.join(self.source_folder, "Lbfgsb.3.0"), self.source_folder)
        copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "Windows" and self.options.shared:
            tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "License.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["lbfgsb"]
        self.cpp_info.includedirs = []
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs = ["m"]
        self.fortran.add_runtime_to_cpp_info(self.cpp_info)
