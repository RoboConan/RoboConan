import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class SuiteSparseMongooseConan(ConanFile):
    name = "suitesparse-mongoose"
    description = "Mongoose: Graph partitioning library in SuiteSparse"
    license = "GPL-3.0-only"
    homepage = "https://people.engr.tamu.edu/davis/suitesparse.html"
    topics = ("graph-algorithms", "mathematics", "sparse-matrix", "graph-partitioning")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # BLAS and OpenMP are provided via suitesparse-config
        self.requires("suitesparse-config/[^7.8.3]", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["SUITESPARSE_USE_OPENMP"] = True
        tc.variables["SUITESPARSE_USE_CUDA"] = False
        tc.variables["SUITESPARSE_DEMOS"] = False
        tc.variables["SUITESPARSE_USE_FORTRAN"] = False  # Fortran sources are translated to C instead
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        # Python is only used for tests
        replace_in_file(self, os.path.join(self.source_folder, "Mongoose", "CMakeLists.txt"),
                        "find_package ( Python COMPONENTS Interpreter )", "")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder="Mongoose")
        cmake.build()

    def package(self):
        copy(self, "License.txt", os.path.join(self.source_folder, "Mongoose", "Doc"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SuiteSparse_Mongoose")
        self.cpp_info.set_property("cmake_target_name", "SuiteSparse::Mongoose")
        if not self.options.shared:
            self.cpp_info.set_property("cmake_target_aliases", ["SuiteSparse::Mongoose_static"])
        self.cpp_info.set_property("pkg_config_name", "Mongoose")

        suffix = "_static" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.libs = ["suitesparse_mongoose" + suffix]
        self.cpp_info.includedirs.append("include/suitesparse")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
