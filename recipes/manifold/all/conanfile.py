import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class ManifoldConan(ConanFile):
    name = "manifold"
    description = "Geometry library for topological robustness"
    license = "Apache-2.0"
    homepage = "https://github.com/elalish/manifold"
    topics = ("geometry", "topological", "mesh")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_clipper2": [True, False],
        "with_tbb": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_clipper2": True,
        "with_tbb": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_clipper2:
            # For CrossSection for 2D support
            self.requires("clipper2/1.4.0")
        if self.options.with_tbb:
            self.requires("onetbb/[>=2021]")

    def validate(self):
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_EXTENSIONS OFF)", "")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["MANIFOLD_DOWNLOADS"] = False
        tc.cache_variables["MANIFOLD_TEST"] = False
        tc.cache_variables["MANIFOLD_CBIND"] = False
        tc.cache_variables["MANIFOLD_PYBIND"] = False
        tc.cache_variables["MANIFOLD_STRICT"] = False # no -Werror
        tc.cache_variables["MANIFOLD_CROSS_SECTION"] = self.options.with_clipper2
        tc.cache_variables["MANIFOLD_PAR"] = self.options.with_tbb
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.with_clipper2:
            deps.set_property("clipper2::clipper2", "cmake_target_name", "Clipper2")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "manifold")
        self.cpp_info.set_property("cmake_target_name", "manifold::manifold")
        self.cpp_info.set_property("pkg_config_name", "manifold")

        self.cpp_info.libs = ["manifold"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")

        if self.options.with_clipper2:
            self.cpp_info.defines.append("MANIFOLD_CROSS_SECTION")
        if self.options.with_tbb:
            self.cpp_info.defines.append("MANIFOLD_PAR=1")
