import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class CppADConan(ConanFile):
    name = "cppad"
    description = "CppAD: a C++ algorithmic differentiation package"
    license = "EPL-2.0 OR GPL-2.0-or-later"
    homepage = "https://cppad.readthedocs.io/"
    topics = ("algorithmic-differentiation", "automatic-differentiation", "autodiff")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ipopt": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ipopt": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        self.requires("boost/[^1.71.0]", libs=False)
        # Used in a cppad/utility/omp_alloc.hpp public header
        self.requires("openmp/system", transitive_headers=True)
        if self.options.with_ipopt:
            self.requires("coin-ipopt/[^3.14.13]", transitive_headers=True, transitive_libs=True)
        # self.requires("adolc/[^2.7.2]")
        # self.requires("colpack/[^1.0.10]")
        # self.requires("sacado/[^15.0.0]")
        # self.requires("fadbad/[^2.1.0]")

    def validate(self):
        check_min_cppstd(self, 11)
        # sacado support requires C++17

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["cppad_static_lib"] = not self.options.shared
        tc.cache_variables["include_ipopt"] = self.options.with_ipopt
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "cppad")
        self.cpp_info.libs = ["cppad_lib"]
        if self.options.with_ipopt:
            self.cpp_info.libs.append("cppad_ipopt")
