import os
from functools import cached_property

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *


class HyperionConan(ConanFile):
    name = "hyperion"
    description = "Symbolic Continuous-Time Gaussian Belief Propagation Framework with Ceres Interoperability"
    license = "BSD-3-Clause"
    homepage = "https://github.com/VIS4ROB-lab/hyperion"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "shared": [True, False],
        "build_benchmarks": [True, False],
    }
    default_options = {
        "fPIC": True,
        "shared": False,
        "build_benchmarks": False,
        "symforce/*:build_opt": True,
    }
    implements = ["auto_shared_fpic"]

    @cached_property
    def _enable_tests(self):
        return not self.conf.get("tools.build:skip_test", default=True, check_type=bool)

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        check_min_cppstd(self, 20)

    def requirements(self):
        self.requires("symforce/0.11-git.20260328", transitive_headers=True, transitive_libs=True)
        self.requires("ceres-solver/[~2.2]", transitive_headers=True, transitive_libs=True)
        self.requires("abseil/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/[>=3 <6]", transitive_headers=True, transitive_libs=True)
        self.requires("glog/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("yaml-cpp/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("boost/[^1]", transitive_headers=True, libs=False)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22]")
        if self._enable_tests or self.options.build_benchmarks:
            self.test_requires("catch2/[^3]")
        if self.options.build_benchmarks:
            self.test_requires("basalt-headers/0.1.0")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = self._enable_tests
        tc.variables["BUILD_BENCHMARKS"] = self.options.build_benchmarks
        tc.variables["BUILD_EXAMPLES"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self._enable_tests:
            cmake.test()

    @property
    def _python_site_packages(self):
        return os.path.join(self.package_folder, "lib/python3/site-packages")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "*",
             os.path.join(self.source_folder, "codegen"),
             os.path.join(self._python_site_packages, "hyperion"))
        save(self, os.path.join(self._python_site_packages, "__init__.py"), "")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "hyperion")
        self.cpp_info.set_property("cmake_target_name", "hyperion::hyperion")
        self.cpp_info.libs = ["hyperion"]
        self.cpp_info.requires = [
            "symforce::symforce",
            "abseil::base",
            "abseil::flat_hash_map",
            "abseil::strings",
            "ceres-solver::ceres-solver",
            "eigen::eigen",
            "glog::glog",
            "yaml-cpp::yaml-cpp",
            "fmt::fmt",
            "boost::headers",
        ]
        self.runenv_info.prepend_path("PYTHONPATH", self._python_site_packages)
