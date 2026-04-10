import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class BasaltConan(ConanFile):
    name = "basalt"
    description = "Basalt: Visual-Inertial Mapping with Non-Linear Factor Recovery"
    license = "BSD-3-Clause"
    homepage = "https://cvg.cit.tum.de/research/vslam/basalt"
    topics = ("computer-vision", "slam", "vio", "calibration", "mapping")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "instantiations_double": [True, False],
        "instantiations_float": [True, False],
        "with_cholmod": [True, False],
        "with_realsense": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "instantiations_double": False,
        "instantiations_float": False,
        "with_cholmod": False,
        "with_realsense": False,

        "opencv/*:calib3d": True,
        "opencv/*:features2d": True,
        "opencv/*:imgcodecs": True,
        "opencv/*:imgproc": True,

        # Basalt sets EIGEN_DONT_PARALLELIZE
        # "eigen/*:with_openmp": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if not self.options.tools:
            self.options.with_realsense.value = False

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("basalt-headers/[~0.1.0]", transitive_headers=True, transitive_libs=True)
        self.requires("onetbb/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("nlohmann_json/[^3]")
        self.requires("magic_enum/[>=0.8 <1]")
        self.requires("pangolin/[>=0.8 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("opengv/[*]")
        self.requires("opencv/[^4]")
        self.requires("rosbag/[^1]")
        if self.options.with_cholmod:
            self.requires("suitesparse-cholmod/[^5]", transitive_headers=True, transitive_libs=True)
        if self.options.tools:
            self.requires("cli11/[^2]")
            if self.options.with_realsense:
                self.requires("librealsense/[^2.50]")

    def validate(self):
        check_min_cppstd(self, 17)
        opencv_opt = self.dependencies["opencv"].options
        if not all([opencv_opt.calib3d, opencv_opt.features2d, opencv_opt.imgcodecs, opencv_opt.imgproc]):
            raise ConanInvalidConfiguration("calib3d, features2d, imgcodecs, imgproc OpenCV modules must be enabled")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.24]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        rmdir(self, "cmake_modules")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BASALT_BUILD_SHARED_LIB"] = self.options.shared
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BASALT_BUILD_TOOLS"] = self.options.tools
        tc.cache_variables["BASALT_INSTANTIATIONS_DOUBLE"] = self.options.instantiations_double
        tc.cache_variables["BASALT_INSTANTIATIONS_FLOAT"] = self.options.instantiations_float
        tc.cache_variables["BASALT_USE_CHOLMOD"] = self.options.with_cholmod
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_realsense2"] = self.options.with_realsense
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_realsense2"] = not self.options.with_realsense
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("cli11", "cmake_target_name", "basalt::cli11")
        deps.set_property("magic_enum", "cmake_target_name", "basalt::magic_enum")
        deps.set_property("fmt", "cmake_target_name", "fmt::fmt")
        deps.set_property("rosbag", "cmake_target_name", "rosbag")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_target_name", "basalt::basalt")
        self.cpp_info.libs = ["basalt"]
        self.cpp_info.resdirs = ["etc"]
        if self.options.with_cholmod:
            self.cpp_info.defines.append("BASALT_USE_CHOLMOD")
