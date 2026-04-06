import os
import textwrap

from conan import ConanFile
from conan.tools.build import check_min_cppstd, can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
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
        "build_python": [True, False],
        "skymarshal_printing": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "build_opt": True,
        "build_python": False,
        "skymarshal_printing": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        if self.options.build_python:
            self.options.build_opt.value = True

    def validate(self):
        check_min_cppstd(self, 20)

    def requirements(self):
        self.requires("eigen/[>=3.4 <6]", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.build_opt:
            self.requires("spdlog/[*]", transitive_headers=True, transitive_libs=True)
            self.requires("metis/[^5]", transitive_headers=True)
        if self.options.build_python:
            self.requires("cpython/[<3.13]")
            self.requires("pybind11/[*]")
            self.requires("symengine/0.7.0-symforce.20250325")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.19 <5]")
        if self.options.build_python:
            self.tool_requires("cpython/<host_version>")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True,
            excludes=["*/third_party/symengine/*"])
        apply_conandata_patches(self)
        if self.version != "0.10.1":
            replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        replace_in_file(self, "symforce/opt/CMakeLists.txt",
                        "add_metis()",
                        "find_package(metis REQUIRED)")
        rm(self, "FindPython.cmake", "third_party/symenginepy/cmake")

    def generate(self):
        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION_FOR_SKYMARSHAL"] = "0.0.1"
        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION_FOR_SYMFORCE_SYM"] = "0.0.1"
        python_version = "3.12"
        if "cpython" in self.dependencies:
            python_version = str(self.dependencies["cpython"].ref.version)
        pyenv = PyEnv(self, py_version=python_version)
        with chdir(self, self.source_folder):
            reqs = "requirements_build.txt" if self.version == "0.10.1" else "requirements/build_py312.txt"
            pyenv.install(["-r", reqs, "cython<3"])
        pyenv.generate()
        if self.options.build_python and can_run(self):
            venv = VirtualRunEnv(self)
            venv.generate(scope="build")

        tc = CMakeToolchain(self)
        tc.cache_variables["SYMFORCE_BUILD_STATIC_LIBRARIES"] = not self.options.shared
        tc.cache_variables["SYMFORCE_BUILD_OPT"] = self.options.build_opt
        tc.cache_variables["SYMFORCE_BUILD_CC_SYM"] = self.options.build_python
        tc.cache_variables["SYMFORCE_BUILD_SYMENGINE"] = self.options.build_python
        tc.cache_variables["SYMFORCE_BUILD_EXAMPLES"] = False
        tc.cache_variables["SYMFORCE_BUILD_TESTS"] = False
        tc.cache_variables["SYMFORCE_ADD_PYTHON_TESTS"] = False
        tc.cache_variables["SYMFORCE_BUILD_BENCHMARKS"] = False
        tc.cache_variables["SYMFORCE_GENERATE_MANIFEST"] = False
        tc.cache_variables["SYMFORCE_SKYMARSHAL_PRINTING"] = self.options.skymarshal_printing
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        tc.cache_variables["SYMFORCE_PYTHON_OVERRIDE"] = os.path.join(pyenv.bin_path, "python").replace("\\", "/")
        tc.cache_variables["CYTHON_BIN"] = os.path.join(pyenv.bin_path, "cython").replace("\\", "/")
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("metis", "cmake_target_name", "metis")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if self.options.build_python:
            mkdir(self, os.path.join(self.build_folder, "python_package"))
            with chdir(self, os.path.join(self.build_folder, "python_package")):
                copy(self, "*", os.path.join(self.build_folder, "pybind"), ".")
                copy(self, "*", os.path.join(self.build_folder, "symengine_install"), ".")
                copy(self, "*", os.path.join(self.build_folder, "lcmtypes/python2.7"), ".")
                copy(self, "*", os.path.join(self.source_folder, "symforce"), "symforce")
                copy(self, "*", os.path.join(self.source_folder, "gen/python/sym"), "sym")
                copy(self, "*", os.path.join(self.source_folder, "third_party/skymarshal/skymarshal"), "skymarshal")
                rm(self, "pyproject.toml", ".", recursive=True)
                save(self, "symforce_requirements.txt", textwrap.dedent("""\
                    ruff
                    clang-format
                    graphviz
                    jinja2
                    numpy
                    scipy
                    sympy>=1.11
                    sortedcontainers
                """))

    @property
    def _python_package_dir(self):
        # TODO: Python package dir should be specific to Python version and OS
        return os.path.join(self.package_folder, "lib/python3/site-packages")

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        if self.options.build_python:
            copy(self, "*", os.path.join(self.build_folder, "python_package"), self._python_package_dir)

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

        if self.options.build_python:
            self.cpp_info.components["_python"].requires = ["opt", "slam", "cpython::cpython", "pybind11::pybind11", "symengine::symengine"]
            self.runenv_info.prepend_path("PYTHONPATH", self._python_package_dir)
