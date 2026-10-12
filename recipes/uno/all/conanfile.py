import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class UnoConan(ConanFile):
    name = "uno"
    description = "Uno (Unifying Nonlinear Optimization) - A modular optimization solver"
    license = "MIT"
    homepage = "https://github.com/cvanaret/Uno"
    topics = ("optimization", "nonlinear-programming", "mathematical-optimization", "solver")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_asl": [True, False],
        "with_bqpd": [True, False],
        "with_hsl": [True, False],
        "hsl_runtime_loading": [True, False],
        "with_highs": [True, False],
        "with_mumps": [True, False],
        "with_metis": [True, False],
        "with_spral": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_asl": False,
        "with_bqpd": True,
        "with_hsl": False,
        "hsl_runtime_loading": False,
        "with_highs": True,
        "with_mumps": False,
        "with_metis": True,
        "with_spral": False,
    }
    implements = ["auto_shared_fpic"]

    @property
    def _fortran_compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return executables.get("fortran")

    def configure(self):
        if self.options.get_safe("hsl_runtime_loading"):
            self.options.with_hsl.value = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("blas/latest")
        self.requires("lapack/latest")
        if self.options.with_asl:
            self.requires("ampl-asl/[^1]")
        if self.options.with_bqpd:
            self.requires("bqpd_jll/[^1]")
        if self.options.with_hsl and not self.options.get_safe("hsl_runtime_loading"):
            self.requires("coin-hsl/[*]")
        if self.options.with_highs:
            self.requires("highs/[^1.7]")
        if self.options.with_mumps:
            self.requires("coin-mumps/[^3.0.5]")
        if self.options.with_metis:
            self.requires("metis/[^5.2.1]")
        if self.options.with_spral:
            self.requires("spral/[*]")

    def validate(self):
        check_min_cppstd(self, 17)
        if self.options.get_safe("hsl_runtime_loading") and not self.options.shared:
            raise ConanInvalidConfiguration("hsl_runtime_loading=True requires shared=True")

    def validate_build(self):
        if not self._fortran_compiler:
            raise ConanInvalidConfiguration(
                "A Fortran compiler is required. "
                "Please provide one by setting tools.build:compiler_executables={'fortran': '...'}."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        rm(self, "Find*.cmake", self.source_folder, recursive=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["ENABLE_TESTS"] = False
        tc.cache_variables["UNO_PYBIND11_DETAILED_ERRORS"] = False
        tc.cache_variables["USE_OPENMP"] = False
        tc.cache_variables["WITH_ASL"] = self.options.with_asl
        tc.cache_variables["WITH_BQPD"] = self.options.with_bqpd
        tc.cache_variables["WITH_HIGHS"] = self.options.with_highs
        hsl_runtime_loading = self.options.get_safe("hsl_runtime_loading", False)
        if not hsl_runtime_loading:
            tc.cache_variables["WITH_HSL"] = self.options.with_hsl
        tc.cache_variables["HSL_RUNTIME_LOADING"] = hsl_runtime_loading
        tc.cache_variables["WITH_METIS"] = self.options.with_metis
        tc.cache_variables["WITH_MUMPS"] = self.options.with_mumps
        tc.cache_variables["WITH_SPRAL"] = self.options.with_spral
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("bqpd_jll", "cmake_file_name", "BQPD")
        deps.set_property("bqpd_jll::bqpd", "cmake_target_name", "BQPD::BQPD")
        deps.set_property("coin-hsl", "cmake_file_name", "HSL")
        deps.set_property("coin-hsl", "cmake_target_name", "HSL::HSL")
        deps.set_property("coin-mumps", "cmake_file_name", "MUMPS")
        deps.set_property("coin-mumps", "cmake_target_name", "MUMPS::MUMPS")
        deps.set_property("highs", "cmake_file_name", "HIGHS")
        deps.set_property("highs::highs_", "cmake_target_name", "HIGHS::HIGHS")
        deps.set_property("metis", "cmake_file_name", "METIS")
        deps.set_property("metis", "cmake_target_name", "METIS::METIS")
        deps.set_property("spral", "cmake_file_name", "SPRAL")
        deps.set_property("spral", "cmake_target_name", "SPRAL::SPRAL")
        deps.set_property("ampl-asl::asl", "cmake_target_name", "ampl-asl::asl")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Headers are not installed for some reason
        copy(self, "*.hpp", os.path.join(self.source_folder, "uno"), os.path.join(self.package_folder, "include", "uno"))
        copy(self, "*.h", os.path.join(self.source_folder, "interfaces", "C"),
             os.path.join(self.package_folder, "include", "interfaces", "C"))
        copy(self, "fortran_interface.h", os.path.join(self.build_folder, "include"),
             os.path.join(self.package_folder, "include", "uno"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        uno = self.cpp_info.components["uno"]
        uno.set_property("cmake_target_name", "uno::uno")
        uno.libs = ["uno"]
        uno.includedirs.append("include/uno")
        uno.requires = ["blas::blas", "lapack::lapack"]
        optional_defines = {
            "with_bqpd": "HAS_BQPD",
            "with_highs": "HAS_HIGHS",
            "with_mumps": "HAS_MUMPS",
            "with_spral": "HAS_SPRAL",
            "with_metis": "HAS_METIS",
        }
        for option, define in optional_defines.items():
            if self.options.get_safe(option):
                uno.defines.append(define)
        if self.options.with_bqpd:
            uno.requires.append("bqpd_jll::bqpd")
        if self.options.with_highs:
            uno.requires.append("highs::highs_")
        if self.options.with_hsl:
            uno.defines.append("HAS_HSL")
            if self.options.get_safe("hsl_runtime_loading"):
                uno.defines.append("HSL_RUNTIME_LOADING")
            else:
                uno.requires.append("coin-hsl::coin-hsl")
        if self.options.with_mumps:
            uno.requires.append("coin-mumps::coin-mumps")
        if self.options.with_metis:
            uno.requires.append("metis::metis")
        if self.options.with_spral:
            uno.requires.append("spral::spral")
        if self.settings.os in ["Linux", "FreeBSD"]:
            uno.system_libs = ["m"]
            if self.options.get_safe("hsl_runtime_loading"):
                uno.system_libs.append("dl")

        if self.options.with_asl:
            uno_ampl = self.cpp_info.components["uno_ampl"]
            uno_ampl.set_property("cmake_target_name", "uno::uno_ampl")
            uno_ampl.bindirs = ["bin"]
            uno_ampl.includedirs = []
            uno_ampl.libdirs = []
            uno_ampl.requires = ["uno", "ampl-asl::asl"]
