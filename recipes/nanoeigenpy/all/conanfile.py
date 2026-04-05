import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class NanoeigenpyConan(ConanFile):
    name = "nanoeigenpy"
    description = "A support library for bindings between Eigen in C++ and Python, based on nanobind"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Simple-Robotics/nanoeigenpy"
    topics = ("eigen", "python-bindings", "linear-algebra", "nanobind", "robotics")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "build_module": [True, False],
        "with_cholmod": [True, False],
        "with_accelerate": [True, False],
    }
    default_options = {
        "build_module": False,
        "with_cholmod": False,
        "with_accelerate": True,
    }
    implements = ["auto_shared_fpic"]

    def config_options(self):
        if not is_apple_os(self):
            del self.options.with_accelerate

    def configure(self):
        if not self.options.build_module:
            self.options.rm_safe("with_accelerate")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.4.0 <6]", transitive_headers=True, transitive_libs=True)
        self.requires("nanobind/[^2.5.0]", transitive_headers=True, transitive_libs=True)
        if self.options.get_safe("with_cholmod"):
            self.requires("suitesparse-cholmod/[^5]", transitive_headers=True, transitive_libs=True)
        if self.options.build_module:
            self.requires("cpython/[^3.12]")

    def validate(self):
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22]")
        if self.options.build_module:
            self.tool_requires("cpython/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["INSTALL_DOCUMENTATION"] = False
        tc.cache_variables["BUILD_WITH_CHOLMOD_SUPPORT"] = self.options.with_cholmod
        tc.cache_variables["BUILD_WITH_ACCELERATE_SUPPORT"] = self.options.get_safe("with_accelerate", False)
        if self.options.build_module:
            tc.cache_variables["Python_EXECUTABLE"] = os.path.join(self.dependencies.build["cpython"].package_folder, "bin", "python").replace("\\", "/")
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("suitesparse-cholmod", "cmake_target_name", "CHOLMOD::CHOLMOD")
        deps.generate()

    @property
    def _python_sitelib(self):
        v = self.dependencies["cpython"].ref.version
        return f"lib/python{v.major}.{v.minor}/site-packages"

    def _patch_sources(self):
        if self.options.build_module:
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            "${Python_SITELIB}", self._python_sitelib.replace("\\", "/"))
        else:
            save(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                 "\nset_target_properties(nanoeigenpy PROPERTIES EXCLUDE_FROM_ALL 1)\n", append=True)
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            "TARGETS ${PROJECT_NAME}\n",
                            "TARGETS ${PROJECT_NAME} EXCLUDE_FROM_ALL\n")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "include", "jrl"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "jrl-cmakemodules"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nanoeigenpy")
        self.cpp_info.set_property("cmake_target_name", "nanoeigenpy::nanoeigenpy_headers")
        self.cpp_info.set_property("pkg_config_name", "nanoeigenpy")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.options.with_cholmod:
            self.cpp_info.defines.append("NANOEIGENPY_HAS_CHOLMOD")
        if self.options.get_safe("with_accelerate"):
            self.cpp_info.frameworks.append("Accelerate")
            self.cpp_info.defines.append("NANOEIGENPY_WITH_ACCELERATE_SUPPORT")

        if self.options.build_module:
            self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, self._python_sitelib))
