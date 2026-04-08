import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class FbgemmConan(ConanFile):
    name = "fbgemm"
    description = ("FBGEMM (Facebook GEneral Matrix Multiplication) is a "
                   "low-precision, high-performance matrix-matrix multiplications "
                   "and convolution library for server-side inference.")
    license = "BSD-3-Clause"
    homepage = "https://github.com/pytorch/FBGEMM"
    topics = ("matrix", "convolution", "linear-algebra", "machine-learning", "gemm")
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

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("asmjit/[>=0.0+git.20240531]", transitive_headers=True, transitive_libs=True)
        self.requires("cpuinfo/[>=0.0+git.20231129]", transitive_headers=True, transitive_libs=True)
        self.requires("openmp/system")

    def validate(self):
        # https://github.com/pytorch/FBGEMM/issues/2074
        if str(self.settings.arch).startswith("arm"):
            raise ConanInvalidConfiguration("FBGEMM does not yet support ARM architectures")
        check_min_cppstd(self, 17)
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.25 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        rmdir(self, os.path.join(self.source_folder, "third_party"))
        replace_in_file(self, "CMakeLists.txt", "-Werror", "")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 20)", "")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_C_STANDARD 17)", "")
        # asmjit and cpuinfo have been unvendored
        replace_in_file(self, 'CMakeLists.txt', "if(NOT TARGET asmjit)", "if(0)")
        replace_in_file(self, "CMakeLists.txt", "if(NOT TARGET cpuinfo)", "if(0)")
        replace_in_file(self, "CMakeLists.txt", "$<TARGET_PDB_FILE:asmjit>", "")
        replace_in_file(self, "CMakeLists.txt", "install(TARGETS asmjit", "# install(TARGETS asmjit")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_PROJECT_fbgemm_INCLUDE"] = "conan_deps.cmake"
        tc.variables["FBGEMM_LIBRARY_TYPE"] = "shared" if self.options.shared else "static"
        tc.variables["FBGEMM_BUILD_TESTS"] = False
        tc.variables["FBGEMM_BUILD_BENCHMARKS"] = False
        tc.variables["FBGEMM_BUILD_DOCS"] = False
        tc.variables["FBGEMM_BUILD_FBGEMM_GPU"] = False
        if not self.settings.get_safe("compiler.cstd"):
            tc.variables["CMAKE_C_STANDARD"] = 99
        if is_msvc(self) and self.settings.build_type == "Debug":
            # Avoid "fatal error C1128: number of sections exceeded object file format limit: compile with /bigobj"
            tc.extra_cflags.append("/bigobj")
            tc.extra_cxxflags.append("/bigobj")
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        try:
            cmake.build()
        except ConanException:
            self.conf.define("tools.build:jobs", 1)
            cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fbgemmLibrary")
        self.cpp_info.set_property("cmake_target_name", "fbgemm")
        self.cpp_info.libs = ["fbgemm"]
        if not self.options.shared:
            self.cpp_info.defines = ["FBGEMM_STATIC"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
