import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class PoselibConan(ConanFile):
    name = "poselib"
    description = "PoseLib: minimal solvers for calibrated camera pose estimation"
    license = "BSD-3-Clause"
    homepage = "https://github.com/PoseLib/PoseLib"
    topics = ("pose", "camera", "estimation", "solver")
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

    def config_options(self):
        # PoseLib does not export symbols for a shared build on Windows
        if self.settings.os == "Windows":
            del self.options.shared
            del self.options.fPIC
            self.package_type = "static-library"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "-Werror -fPIC", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["ENABLE_ASAN"] = False
        tc.cache_variables["MARCH_NATIVE"] = False
        tc.cache_variables["PYTHON_PACKAGE"] = False
        tc.cache_variables["WITH_BENCHMARK"] = False
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.generate()
        deps = CMakeDeps(self)
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

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PoseLib")
        self.cpp_info.set_property("cmake_target_name", "PoseLib::PoseLib")

        suffix = "d" if self.settings.build_type == "Debug" else ""
        self.cpp_info.libs = ["PoseLib" + suffix]
        self.cpp_info.defines = [f"POSELIB_DEBUG={1 if self.settings.build_type == 'Debug' else 0}"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
