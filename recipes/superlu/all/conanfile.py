import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class SuperLUConan(ConanFile):
    name = "superlu"
    description = "SuperLU is a general purpose library for the direct solution of large, sparse, nonsymmetric systems of linear equations."
    license = "BSD-3-Clause"
    homepage = "https://github.com/xiaoyeli/superlu"
    topics = ("linear-algebra", "sparse-matrix", "lu-factorization", "scientific-computing")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_single": [True, False],
        "enable_double": [True, False],
        "enable_complex": [True, False],
        "enable_complex16": [True, False],
    }

    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_single": True,
        "enable_double": True,
        "enable_complex": True,
        "enable_complex16": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("blas/latest")
        self.requires("metis/[^5.2.1]")

    def validate(self):
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)
        if not any([self.options.enable_single, self.options.enable_double,
                    self.options.enable_complex, self.options.enable_complex16]):
            raise ConanInvalidConfiguration("At least one precision variant must be enabled")
        mangling = self.dependencies["blas"].extension_properties["fortran_name_mangling"]
        if mangling.startswith("upper_") and not mangling.endswith("no_underscore"):
            raise ConanInvalidConfiguration("SuperLU does not support BLAS with upper_underscore or upper_underscore_extra names")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", 'set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")', "")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        mangling = self.dependencies["blas"].extension_properties["fortran_name_mangling"]
        if mangling.startswith("upper_"):
            tc.preprocessor_definitions["UpCase"] = None
        elif mangling.endswith("no_underscore"):
            tc.preprocessor_definitions["NoChange"] = None
        else:
            tc.preprocessor_definitions["Add_"] = None
        tc.cache_variables["CMAKE_PROJECT_SuperLU_INCLUDE"] = "conan_deps.cmake"
        tc.cache_variables["enable_tests"] = False
        tc.cache_variables["enable_examples"] = False
        tc.cache_variables["enable_doc"] = False
        tc.cache_variables["enable_matlabmex"] = False
        tc.cache_variables["enable_single"] = self.options.enable_single
        tc.cache_variables["enable_double"] = self.options.enable_double
        tc.cache_variables["enable_complex"] = self.options.enable_complex
        tc.cache_variables["enable_complex16"] = self.options.enable_complex16
        tc.cache_variables["enable_fortran"] = False
        tc.cache_variables["enable_internal_blaslib"] = False
        tc.cache_variables["TPL_ENABLE_INTERNAL_BLASLIB"] = False
        tc.cache_variables["TPL_ENABLE_METISLIB"] = True
        tc.cache_variables["TPL_METIS_LIBRARIES"] = "metis::metis"
        tc.cache_variables["TPL_METIS_INCLUDE_DIRS"] = ";"
        tc.cache_variables["XSDK_INDEX_SIZE"] = 64 if self.dependencies["blas"].options.interface == "ilp64" else 32
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
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "superlu")
        self.cpp_info.set_property("cmake_target_name", "superlu::superlu")
        self.cpp_info.set_property("pkg_config_name", "superlu")
        self.cpp_info.libs = ["superlu"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
