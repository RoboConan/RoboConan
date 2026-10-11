import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class GlimExtPackage(ConanFile):
    name = "glim_ext"
    description = "glim_ext is a set of extension modules for GLIM, a 3D LiDAR mapping framework."
    license = "GPL-3.0-only"
    homepage = "https://github.com/koide3/glim_ext"
    topics = ("localization", "mapping", "gpu", "ros", "imu", "lidar", "slam", "3d", "rgb-d")

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "velsupp": [True, False],
        "imuval": [True, False],
        "gravity": [True, False],
        "flatearther": [True, False],
        "dbow": [True, False],
        # TODO:
        # "scan_context": [True, False],
        # "orbslam": [True, False],
    }
    default_options = {
        "velsupp": True,
        "imuval": True,
        "gravity": True,
        "flatearther": True,
        "dbow": False,
        # "scan_context": True,
        # "orbslam": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glim/[^1.2.2]", transitive_headers=True, transitive_libs=True)
        if self.options.dbow:
            self.requires("boost/[^1.71.0]")
        if self.options.imuval or self.options.gravity:
            self.requires("iridescence/[>=0.1.3 <2]")
            self.requires("implot/[<2]")
        # TODO: add ScanContext for scan_context
        # TODO: add ORB_SLAM3 for orbslam
        # TODO: unvendor DBow2 and DBow3

    def validate(self):
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_ORBSLAM"] = False  # self.options.orbslam
        tc.variables["ENABLE_VELSUPP"] = self.options.velsupp
        tc.variables["ENABLE_IMUVAL"] = self.options.imuval
        tc.variables["ENABLE_IMUPRED"] = False  # TODO: package its ROS2 dependencies
        tc.variables["ENABLE_GRAVITY"] = self.options.gravity
        tc.variables["ENABLE_DESKEWING"] = False  # TODO: package its ROS2 dependencies
        tc.variables["ENABLE_FASTLIO2"] = False  # TODO: package FAST_LIO and PCL dependencies
        tc.variables["ENABLE_SCAN_CONTEXT"] = False  # self.options.scan_context
        tc.variables["ENABLE_DBOW"] = self.options.dbow
        tc.variables["ENABLE_GNSS"] = False  # Requires ROS1 or ROS2
        tc.variables["ENABLE_FLATEARTHER"] = self.options.flatearther
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("gtsam", "cmake_target_name", "GTSAM::GTSAM")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # No license file in the repo
        # copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "*.json", os.path.join(self.source_folder, "config"),
             os.path.join(self.package_folder, "share", "glim_ext", "config"))
        if self.options.dbow:
            copy(self, "orbvoc.dbow3",
                 os.path.join(self.source_folder, "modules", "mapping", "dbow_loop_detector", "thirdparty", "DBoW3"),
                 os.path.join(self.package_folder, "share", "glim_ext", "data"))
            copy(self, "LICENSE.txt",
                 os.path.join(self.source_folder, "modules", "mapping", "dbow_loop_detector", "thirdparty", "DBoW3"),
                 os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.resdirs = ["share/glim_ext/config"]
        if self.options.dbow:
            self.cpp_info.resdirs.append("share/glim_ext/data")
        self.cpp_info.libs = ["glim_ext", "glim_callback_demo", "logger_hook_demo"]
        if self.options.velsupp:
            self.cpp_info.libs.append("velocity_suppressor")
        if self.options.imuval:
            self.cpp_info.libs.append("imu_validator")
        if self.options.gravity:
            self.cpp_info.libs.append("gravity_estimator")
        if self.options.flatearther:
            self.cpp_info.libs.append("flat_earther")
        if self.options.dbow:
            self.cpp_info.libs.append("dbow_loop_detector")
        self.cpp_info.requires = ["glim::glim"]
        if self.options.dbow:
            self.cpp_info.requires.append("boost::filesystem")
        if self.options.imuval or self.options.gravity:
            self.cpp_info.requires.extend(["iridescence::iridescence", "implot::implot"])
        # if self.options.scan_context:
        #     self.cpp_info.libs.append("scan_context_loop_detector")
        # if self.options.orbslam:
        #     self.cpp_info.libs.append("orb_slam_odometry")
