import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class SuperLuMtConan(ConanFile):
    name = "superlu_mt"
    description = "SuperLU_MT is a parallel extension to the serial SuperLU library."
    license = "BSD-3-Clause"
    homepage = "https://github.com/xiaoyeli/superlu_mt"
    topics = ("linear-algebra", "sparse-matrix", "lu-factorization", "scientific-computing", "parallel")
    # provides = ["superlu"]
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "threading": ["pthread", "openmp"],
        "enable_single": [True, False],
        "enable_double": [True, False],
        "enable_complex": [True, False],
        "enable_complex16": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "threading": "openmp",
        "enable_single": True,
        "enable_double": True,
        "enable_complex": True,
        "enable_complex16": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Unvendoring COLAMD causes missing symbols in Octave
        # self.requires("suitesparse-colamd/[*]")
        self.requires("blas/latest")
        if self.options.threading == "openmp":
            self.requires("openmp/system")

    def validate(self):
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)
        if not any([self.options.enable_single, self.options.enable_double,
                    self.options.enable_complex, self.options.enable_complex16]):
            raise ConanInvalidConfiguration("At least one precision variant must be enabled")
        mangling = self.dependencies["blas"].extension_properties["fortran_name_mangling"]
        if mangling.startswith("upper_") and not mangling.endswith("no_underscore"):
            raise ConanInvalidConfiguration("SuperLU_MT does not support BLAS with upper_underscore or upper_underscore_extra names")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "SRC/CMakeLists.txt", "PRIVATE Add_)", "PRIVATE ${SUPERLU_FORTRAN})")
        # rm(self, "colamd.*", "SRC")
        # save(self, "SRC/CMakeLists.txt",
        #      "\nfind_package(COLAMD REQUIRED)\n"
        #      "target_link_libraries (superlu_mt${PLAT} PRIVATE SuiteSparse::COLAMD)\n", append=True)

    def generate(self):
        tc = CMakeToolchain(self)
        mangling = self.dependencies["blas"].extension_properties["fortran_name_mangling"]
        if mangling.startswith("upper_"):
            tc.cache_variables["SUPERLU_FORTRAN"] = "UpCase"
        elif mangling.endswith("no_underscore"):
            tc.cache_variables["SUPERLU_FORTRAN"] = "NoChange"
        else:
            tc.cache_variables["SUPERLU_FORTRAN"] = "Add_"
        tc.cache_variables["PLAT"] = "_OPENMP" if self.options.threading == "openmp" else "_PTHREAD"
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
        tc.cache_variables["LONGINT"] = self.dependencies["blas"].options.interface == "ilp64"
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
        rm(self, "colamd.h", os.path.join(self.package_folder, "include", "superlu_mt"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "superlu_mt")
        self.cpp_info.set_property("cmake_target_name", "superlu_mt::superlu_mt")
        self.cpp_info.set_property("pkg_config_name", "superlu_mt")
        libname = "superlu_mt"
        libname += "_OPENMP" if self.options.threading == "openmp" else "_PTHREAD"
        self.cpp_info.libs = [libname]
        self.cpp_info.includedirs.append("include/superlu_mt")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]
