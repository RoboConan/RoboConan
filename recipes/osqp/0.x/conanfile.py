import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.files import *

required_conan_version = ">=2.4"


class OsqpConan(ConanFile):
    name = "osqp"
    package_type = "library"
    description = "The OSQP (Operator Splitting Quadratic Program) solver is a numerical optimization package."
    license = "Apache-2.0"
    homepage = "https://osqp.org/"
    topics = ("machine-learning", "control", "optimization", "svm", "solver", "lasso", "portfolio-optimization",
              "numerical-optimization", "quadratic-programming", "convex-optimization", "model-predictive-control")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_pardiso": [True, False],
        "float32": [True, False],
        "int32": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_pardiso": True,
        "float32": False,
        "int32": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("qdldl/[>=0.1.9 <1]")
        self.requires("suitesparse-amd/[^3.3.4]")

    def validate(self):
        qdldl_options = self.dependencies["qdldl"].options
        if qdldl_options.float32 != self.options.float32 or qdldl_options.int32 != self.options.int32:
            raise ConanInvalidConfiguration("OSQP and QDLDL must use the same float32 and int32 options")

    @property
    def _for_casadi(self):
        return "casadi" in self.version

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # CMake v4 support
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required (VERSION 3.2)",
                        "cmake_minimum_required (VERSION 3.5)")
        # Make shared builds conditional
        replace_in_file(self, "CMakeLists.txt",
                        "NOT PYTHON AND NOT MATLAB AND NOT R_LANG" if self._for_casadi else
                        "NOT PYTHON AND NOT MATLAB AND NOT R_LANG AND NOT EMBEDDED",
                        "BUILD_SHARED_LIBS")
        # Unvendor QDLDL and AMD
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_POSITION_INDEPENDENT_CODE ON)  # -fPIC",
                        "find_package(qdldl REQUIRED)\n"
                        "find_package(AMD REQUIRED)\n"
                        "link_libraries(qdldl::qdldl SuiteSparse::AMD)")
        rmdir(self, "lin_sys/direct/qdldl/amd")
        save(self, "lin_sys/direct/qdldl/CMakeLists.txt", textwrap.dedent("""\
            add_library(linsys_qdldl OBJECT qdldl_interface.c)
            include_directories(${CMAKE_SOURCE_DIR}/include)
        """))
        replace_in_file(self, "lin_sys/direct/CMakeLists.txt", "$<TARGET_OBJECTS:qdldlobject>", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["ENABLE_MKL_PARDISO"] = self.options.enable_pardiso
        tc.variables["OSQP_BUILD_DEMO_EXE"] = False
        tc.variables["COVERAGE"] = False
        tc.variables["UNITTESTS"] = False
        tc.variables["PRINTING"] = not self._for_casadi
        tc.variables["PROFILING"] = False
        tc.variables["CTRLC"] = not self._for_casadi
        tc.variables["DFLOAT"] = self.options.float32
        tc.variables["DLONG"] = not self.options.int32
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        if self.options.shared:
            # Don't build static
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            "install(TARGETS osqpstatic",
                            "message(TRACE # install(TARGETS osqpstatic")
            save(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                 "\nset_target_properties(osqpstatic PROPERTIES EXCLUDE_FROM_ALL 1)\n",
                 append=True)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "osqp")
        self.cpp_info.set_property("cmake_target_name", "osqp::osqp")
        self.cpp_info.libs = ["osqp"]
        self.cpp_info.includedirs.append("include/osqp")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
