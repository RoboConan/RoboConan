import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class ScsConan(ConanFile):
    name = "scs"
    description = "SCS (splitting conic solver) is a numerical optimization package for solving large-scale convex cone problems."
    license = "MIT"
    homepage = "https://github.com/cvxgrp/scs"
    topics = ("optimization", "convex-programming", "conic", "solver", "numerical")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "sfloat": [True, False],
        "dlong": [True, False],
        "use_spectral_cones": [True, False],
        "with_lapack": [True, False],
        "with_openmp": [True, False],
        "with_mkl": [True, False],
        "with_cudss": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "sfloat": False,
        "dlong": False,
        "use_spectral_cones": False,
        "with_lapack": True,
        "with_openmp": True,
        "with_mkl": False,
        "with_cudss": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cudss:
            del self.settings.cuda

    def package_id(self):
        if self.info.options.with_cudss:
            del self.info.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_lapack:
            self.requires("lapack/latest")
        if self.options.with_mkl:
            self.requires("onemkl/[*]")
        if self.options.with_openmp:
            self.requires("openmp/system")
        if self.options.with_cudss:
            self.cuda.requires("cudart")
            self.cuda.requires("cudss")

    def validate(self):
        if not self.options.with_lapack and self.options.use_spectral_cones:
            raise ConanInvalidConfiguration("use_spectral_cones requires with_lapack")
        if self.options.with_cudss and self.options.dlong:
            raise ConanInvalidConfiguration("cuDSS requires 32-bit integers (dlong=False)")
        if self.options.with_lapack:
            mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
            if not mangling.startswith("lower_"):
                raise ConanInvalidConfiguration("SCS requires BLAS/LAPACK name mangling to be lower_no_underscore, lower_underscore, or lower_underscore_extra")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.options.with_lapack:
            mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
            if mangling.endswith("no_underscore"):
                tc.preprocessor_definitions["NOBLASSUFFIX"] = "1"
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["SFLOAT"] = self.options.sfloat
        tc.cache_variables["DLONG"] = self.options.dlong
        tc.cache_variables["USE_LAPACK"] = self.options.with_lapack
        tc.cache_variables["USE_MKL"] = self.options.with_mkl
        tc.cache_variables["USE_SPECTRAL_CONES"] = self.options.use_spectral_cones
        tc.cache_variables["USE_OPENMP"] = self.options.with_openmp
        tc.cache_variables["USE_CUDSS"] = self.options.with_cudss
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

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "scs")

        self.cpp_info.components["scsdir"].set_property("cmake_target_name", "scs::scsdir")
        self.cpp_info.components["scsdir"].libs = ["scsdir"]
        self.cpp_info.components["scsdir"].requires = []

        self.cpp_info.components["scsindir"].set_property("cmake_target_name", "scs::scsindir")
        self.cpp_info.components["scsindir"].libs = ["scsindir"]
        self.cpp_info.components["scsindir"].requires = []

        if self.options.with_mkl:
            self.cpp_info.components["scsmkl"].set_property("cmake_target_name", "scs::scsmkl")
            self.cpp_info.components["scsmkl"].libs = ["scsmkl"]
            self.cpp_info.components["scsmkl"].requires = ["onemkl::onemkl"]

        if self.options.with_cudss:
            self.cpp_info.components["scscudss"].set_property("cmake_target_name", "scs::scscudss")
            self.cpp_info.components["scscudss"].libs = ["scscudss"]
            self.cpp_info.components["scscudss"].requires = ["cudart::cudart_", "cudss::cudss_"]

        for _, component in self.cpp_info.components.items():
            component.includedirs = ["include/scs"]
            if self.options.use_spectral_cones:
                component.defines.append("USE_SPECTRAL_CONES")
            if self.settings.os in ["Linux", "FreeBSD"]:
                component.system_libs = ["m"]
            if self.options.with_openmp:
                component.requires.append("openmp::openmp")
            if self.options.with_lapack:
                component.requires.append("lapack::lapack")
