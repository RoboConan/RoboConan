import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.21"


class GlimPackage(ConanFile):
    name = "glim"
    description = "GLIM: versatile and extensible range-based 3D localization and mapping framework"
    license = "MIT"
    homepage = "https://github.com/koide3/glim"
    topics = ("localization", "mapping", "gpu", "ros", "imu", "lidar", "slam", "3d", "rgb-d")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "cuda": [True, False],
        "viewer": [True, False],
        "with_opencv": [True, False],
    }
    default_options = {
        "cuda": False,
        "viewer": False,
        "with_opencv": True,
        "boost/*:with_serialization": True,
        "boost/*:with_filesystem": True,
        "boost/*:with_graph": True,
    }

    def configure(self):
        if self.options.with_opencv:
            # Make OpenCV a bit more lightweight
            self.options["opencv"].with_ffmpeg = False
            self.options["opencv"].with_tesseract = False
        if self.options.cuda:
            self.options["gtsam_points"].cuda = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True, transitive_libs=True)
        if self.options.with_opencv:
            self.requires("opencv/[^4.5]", transitive_headers=True, transitive_libs=True)
        self.requires("gtsam/[^4.2]", transitive_headers=True, transitive_libs=True)
        self.requires("gtsam_points/[^1.2.2]", transitive_headers=True, transitive_libs=True)
        self.requires("nlohmann_json/[^3]", transitive_headers=True, transitive_libs=True)
        self.requires("openmp/system")
        self.requires("spdlog/[^1.8 <1.15]", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/[<11]", transitive_headers=True, transitive_libs=True)
        if self.options.viewer:
            self.requires("iridescence/[>=0.1.3 <2]", transitive_headers=True, transitive_libs=True)
        self.requires("boost/[^1.71.0]", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 17)
        if self.options.cuda and not self.dependencies["gtsam_points"].options.cuda:
            raise ConanInvalidConfiguration("-o glim/*:cuda=True requires -o gtsam_points/*:cuda=True")
        if not self.dependencies["boost"].options.with_serialization:
            raise ConanInvalidConfiguration("-o boost/*:with_serialization=True is required")
        if not self.dependencies["boost"].options.with_filesystem:
            raise ConanInvalidConfiguration("-o boost/*:with_filesystem=True is required")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Make sure third-party deps are unvendored
        rmdir(self, "thirdparty")
        # Forbid building as a ROS package with ROS deps
        replace_in_file(self, "CMakeLists.txt", "DEFINED ENV{ROS_VERSION}", "FALSE")
        # GTSAM from Conan does not vendor Eigen
        replace_in_file(self, "src/glim/util/debug.cpp",
                        'logger->debug("GTSAM_EIGEN_VERSION=',
                        '// logger->debug("GTSAM_EIGEN_VERSION=')

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_WITH_CUDA"] = self.options.cuda
        tc.variables["BUILD_WITH_OPENCV"] = self.options.with_opencv
        tc.variables["BUILD_WITH_VIEWER"] = self.options.viewer
        tc.variables["BUILD_WITH_MARCH_NATIVE"] = False
        tc.variables["GTSAM_POINTS_USE_CUDA"] = self.options.cuda
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("gtsam", "cmake_target_name", "GTSAM::GTSAM")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "*.json", os.path.join(self.source_folder, "config"),
             os.path.join(self.package_folder, "share", "glim", "config"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "glim")
        self.cpp_info.set_property("cmake_target_name", "glim::_glim_all")
        self.cpp_info.set_property("cmake_extra_variables", {
            "BUILD_WITH_CUDA": "ON" if self.options.cuda else "OFF",
            "BUILD_WITH_VIEWER": "ON" if self.options.viewer else "OFF",
            "GLIM_USE_OPENCV": 1 if self.options.with_opencv else 0,
        })

        def _add_component(name, reqs=None):
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", f"glim::{name}")
            component.libs = [name]
            component.requires = reqs or []
            if name != "glim":
                component.requires.append("glim")

        main_reqs = [
            "boost::headers",
            "boost::filesystem",
            "boost::serialization",
            "eigen::eigen",
            "gtsam::gtsam",
            "gtsam_points::gtsam_points",
            "nlohmann_json::nlohmann_json",
            "openmp::openmp",
            "spdlog::spdlog",
            "fmt::fmt",
        ]
        if self.options.with_opencv:
            main_reqs.append("opencv::opencv_core")
        if self.options.viewer:
            main_reqs.append("iridescence::iridescence")

        _add_component("glim", main_reqs)
        self.cpp_info.components["glim"].resdirs = ["share/glim/config"]
        if self.options.with_opencv:
            self.cpp_info.components["glim"].defines.append("GLIM_USE_OPENCV")
        _add_component("global_mapping")
        _add_component("global_mapping_pose_graph")
        _add_component("odometry_estimation_cpu")
        _add_component("odometry_estimation_ct")
        _add_component("sub_mapping")
        _add_component("sub_mapping_passthrough")

        if self.options.cuda:
            # CUDA dependency is provided via gtsam_points
            _add_component("odometry_estimation_gpu")

        if self.options.viewer:
            _add_component("interactive_viewer", ["iridescence::iridescence"])
            _add_component("standard_viewer", ["iridescence::iridescence"])
            _add_component("memory_monitor", ["iridescence::iridescence"])
            _add_component("map_editor", ["iridescence::iridescence"])
