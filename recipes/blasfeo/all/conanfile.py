import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class BlasfeoConan(ConanFile):
    name = "blasfeo"
    description = "BLAS For Embedded Optimization - optimized basic linear algebra routines for matrices that fit in cache"
    license = "BSD-2-Clause"
    homepage = "https://github.com/giaf/blasfeo"
    topics = ("blas", "linear-algebra", "embedded", "high-performance")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "use_external_blas": [True, False],
        "target": ["x64_automatic", "x64_intel_skylake_x", "x64_intel_haswell",
                   "x64_intel_sandy_bridge", "x64_intel_core", "x64_amd_bulldozer",
                   "armv8a_apple_m1", "armv8a_arm_cortex_a76", "armv8a_arm_cortex_a73",
                   "armv8a_arm_cortex_a57", "armv8a_arm_cortex_a55", "armv8a_arm_cortex_a53",
                   "armv7a_arm_cortex_a15", "armv7a_arm_cortex_a9", "armv7a_arm_cortex_a7",
                   "generic"],
        "matrix_format": ["column_major", "panel_major"],
        "fortran_blas_api": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "use_external_blas": False,
        "target": "generic",
        "matrix_format": "panel_major",
        "fortran_blas_api": False,
    }
    options_description = {
        "fortran_blas_api": (
            "True: routine names are in the form of dgemm_, dpotrf_, cblas_dgemm.\n"
            "False: routine names are in the form of blasfeo_blas_dgemm, blasfeo_lapack_dpotrf, blasfeo_cblas_dgemm."
        )
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch == "x86_64":
            self.options.target = "x64_intel_skylake_x"
        if is_apple_os(self) and self.settings.arch == "armv8":
            self.options.target = "armv8a_apple_m1"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.use_external_blas:
            del self.options.matrix_format
        if self.settings.compiler == "msvc":
            self.options.target.value = "generic"
        if self.options.fortran_blas_api:
            self.provides = ["blasfeo", "blas", "lapack"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.use_external_blas:
            self.requires("blas/latest")

    def build_requirements(self):
        self.tool_requires("nasm/[*]")
        self.tool_requires("cmake/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if not self.options.use_external_blas:
            tc.cache_variables["LA"] = "HIGH_PERFORMANCE"
            tc.cache_variables["MF"] = "PANELMAJ" if self.options.matrix_format == "panel_major" else "COLMAJ"
        else:
            tc.cache_variables["LA"] = "EXTERNAL_BLAS_WRAPPER"
            tc.cache_variables["EXTERNAL_BLAS"] = "OPENBLAS"
        tc.cache_variables["TARGET"] = str(self.options.target).upper()
        tc.cache_variables["BLAS_API"] = True
        tc.cache_variables["FORTRAN_BLAS_API"] = self.options.fortran_blas_api
        tc.cache_variables["BLASFEO_TESTING"] = False
        tc.cache_variables["BLASFEO_BENCHMARKS"] = False
        tc.cache_variables["BLASFEO_EXAMPLES"] = False
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["CMAKE_INSTALL_PREFIX"] = self.package_folder.replace("\\", "/")
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
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
        rmdir(self, os.path.join(self.package_folder, "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "blasfeo")
        self.cpp_info.set_property("cmake_target_name", "blasfeo")
        self.cpp_info.libs = ["blasfeo"]
        self.cpp_info.defines.append("BLAS_API")
        if self.options.fortran_blas_api:
            self.cpp_info.defines.append("FORTRAN_BLAS_API")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
