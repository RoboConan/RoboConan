import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class RosbagConan(ConanFile):
    name = "rosbag"
    description = "Standalone build of rosbag_storage and its ROS dependencies for non-ROS consumers"
    license = "BSD-3-Clause"
    homepage = "https://wiki.ros.org/rosbag"
    topics = ("ros", "rosbag", "robotics", "serialization")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "boost/*:with_date_time": True,
        "boost/*:with_filesystem": True,
        "boost/*:with_program_options": True,
        "boost/*:with_regex": True,
        "boost/*:with_thread": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.71.0]", transitive_headers=True)
        self.requires("bzip2/[^1.0.8]", transitive_headers=True)
        self.requires("console_bridge/[^1.0]", transitive_headers=True, transitive_libs=True)
        self.requires("lz4/[^1.9]", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 14)
        for comp in ["date_time", "filesystem", "program_options", "regex", "thread"]:
            if not self.dependencies["boost"].options.get_safe(f"with_{comp}"):
                raise ConanInvalidConfiguration(f"-o boost/*:with_{comp}=True is required")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["ros_comm"], destination="ros_comm", strip_root=True)
        get(self, **sources["roscpp_core"], destination="roscpp_core", strip_root=True)
        download(self, **sources["license"], filename="LICENSE")

    def generate(self):
        tc = CMakeToolchain(self)
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

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "rosbag")
        self.cpp_info.set_property("cmake_target_name", "rosbag::rosbag")
        self.cpp_info.libs = ["rosbag"]
        self.cpp_info.requires = [
            "boost::date_time",
            "boost::filesystem",
            "boost::headers",
            "boost::program_options",
            "boost::regex",
            "boost::thread",
            "bzip2::bzip2",
            "console_bridge::console_bridge",
            "lz4::lz4",
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]
