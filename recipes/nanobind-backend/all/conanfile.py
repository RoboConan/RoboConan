import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class PackageConan(ConanFile):
    name = "nanobind-backend"
    description = "Runtime backend for nanobind split-mode extension modules"
    license = "BSD-3-Clause"
    homepage = "https://github.com/wjakob/nanobind"
    topics = ("python", "bindings", "nanobind")

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # The backend binary is specific to CPython's ABI, including whether
        # the interpreter is free-threaded.
        self.info.requires["cpython"].full_package_mode()

    def requirements(self):
        self.requires("cpython/[^3.10]")
        self.requires("tsl-robin-map/[^1.3]")

    def build_requirements(self):
        self.tool_requires("cpython/<host_version>")
        self.tool_requires("cmake/[^4.4]")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["NB_USE_SUBMODULE_DEPS"] = False
        tc.cache_variables["Python_EXECUTABLE"] = os.path.join(self.dependencies.build["cpython"].package_folder, "bin", "python").replace("\\", "/")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="nanobind-backend")
        cmake.build()

    @property
    def _python_sitelib(self):
        if self.settings.os == "Windows":
            return os.path.join("bin", "Lib", "site-packages")
        python = Version(self.dependencies["cpython"].ref.version)
        return os.path.join("lib", f"python{python.major}.{python.minor}", "site-packages")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        site_packages = os.path.join(self.package_folder, self._python_sitelib)
        mkdir(self, site_packages)
        rename(self,
               os.path.join(self.package_folder, "nanobind_backend"),
               os.path.join(site_packages, "nanobind_backend"))
        copy(self, "__init__.py",
             os.path.join(self.source_folder, "nanobind-backend", "src", "nanobind_backend"),
             os.path.join(site_packages, "nanobind_backend"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, self._python_sitelib))
