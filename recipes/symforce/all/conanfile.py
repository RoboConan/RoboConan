import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.system import PyEnv

required_conan_version = ">=2.25"


class SymforceConan(ConanFile):
    name = "symforce"
    description = "Fast symbolic computation, code generation, and nonlinear optimization for robotics"
    license = "Apache-2.0"
    homepage = "https://github.com/symforce-org/symforce"
    topics = ("robotics", "optimization", "factor-graphs", "symbolic-computation", "code-generation")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_opt": [True, False],
        "skymarshal_printing": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "build_opt": True,
        "skymarshal_printing": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        check_min_cppstd(self, 20)

    def requirements(self):
        self.requires("eigen/[>=3.4 <6]", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.build_opt:
            self.requires("spdlog/[*]", transitive_headers=True, transitive_libs=True)
            self.requires("metis/[^5]", transitive_headers=True)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.19 <5]")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        replace_in_file(self, "symforce/opt/CMakeLists.txt",
                        "add_metis()",
                        "find_package(metis REQUIRED)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["SYMFORCE_BUILD_STATIC_LIBRARIES"] = not self.options.shared
        tc.cache_variables["SYMFORCE_BUILD_OPT"] = self.options.build_opt
        tc.cache_variables["SYMFORCE_BUILD_CC_SYM"] = False
        tc.cache_variables["SYMFORCE_BUILD_EXAMPLES"] = False
        tc.cache_variables["SYMFORCE_BUILD_TESTS"] = False
        tc.cache_variables["SYMFORCE_ADD_PYTHON_TESTS"] = False
        tc.cache_variables["SYMFORCE_BUILD_SYMENGINE"] = False
        tc.cache_variables["SYMFORCE_BUILD_BENCHMARKS"] = False
        tc.cache_variables["SYMFORCE_GENERATE_MANIFEST"] = False
        tc.cache_variables["SYMFORCE_SKYMARSHAL_PRINTING"] = self.options.skymarshal_printing
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        tc.cache_variables["WITH_OPENMP"] = False  # Don't accidentally add OpenMP flags from SymEngine
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("metis", "cmake_target_name", "metis")
        deps.generate()

        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION_FOR_SKYMARSHAL"] = "0.0.1"
        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION_FOR_SYMFORCE_SYM"] = "0.0.1"
        pyenv = PyEnv(self)
        with chdir(self, self.source_folder):
            pyenv.install(["-r", os.path.join("requirements", "build_py312.txt")])
        pyenv.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "symforce")
        self.cpp_info.set_property("cmake_target_name", "symforce::symforce")

        # symforce_lcmtypes_cpp: header-only interface target
        self.cpp_info.components["lcmtypes_cpp"].set_property("cmake_target_name", "symforce::symforce_lcmtypes_cpp")
        self.cpp_info.components["lcmtypes_cpp"].requires = ["eigen::eigen", "fmt::fmt"]
        if self.options.skymarshal_printing:
            self.cpp_info.components["lcmtypes_cpp"].defines = ["SKYMARSHAL_PRINTING_ENABLED"]

        # symforce_gen: generated code
        self.cpp_info.components["gen"].set_property("cmake_target_name", "symforce::symforce_gen")
        self.cpp_info.components["gen"].libs = ["symforce_gen"]
        self.cpp_info.components["gen"].requires = ["lcmtypes_cpp"]

        if self.options.build_opt:
            # symforce_cholesky: sparse Cholesky backed by METIS
            self.cpp_info.components["cholesky"].set_property("cmake_target_name", "symforce::symforce_cholesky")
            self.cpp_info.components["cholesky"].libs = ["symforce_cholesky"]
            self.cpp_info.components["cholesky"].requires = ["lcmtypes_cpp", "metis::metis"]

            # symforce_opt: nonlinear optimizer
            self.cpp_info.components["opt"].set_property("cmake_target_name", "symforce::symforce_opt")
            self.cpp_info.components["opt"].libs = ["symforce_opt"]
            self.cpp_info.components["opt"].requires = ["gen", "cholesky", "spdlog::spdlog"]

            # symforce_slam: SLAM-specific factors (IMU preintegration, ...)
            self.cpp_info.components["slam"].set_property("cmake_target_name", "symforce::symforce_slam")
            self.cpp_info.components["slam"].libs = ["symforce_slam"]
            self.cpp_info.components["slam"].requires = ["gen", "opt"]
