import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class DsdpConan(ConanFile):
    name = "dsdp"
    description = "DSDP is a open source implementation of an interior-point method for semidefinite programming."
    license = "DSDP"
    homepage = "https://www.mcs.anl.gov/hs/software/DSDP/"
    topics = ("optimization", "semidefinite-programming", "interior-point")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "timing": ["none", "dsdp_time", "dsdp_ms_time"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "timing": "none",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        if mangling.startswith("upper_"):
            tc.preprocessor_definitions["CAPSBLAS"] = None
        if mangling.endswith("no_underscore"):
            tc.preprocessor_definitions["NOUNDERBLAS"] = None
        tc.cache_variables["DSDPTIMER"] = str(self.options.timing).upper()
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "dsdp-license", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_target_aliases", ["dsdp"])
        self.cpp_info.libs = ["dsdp"]
