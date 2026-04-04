import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class DynamicGraphConan(ConanFile):
    name = "dynamic-graph"
    description = "Efficient data-flow library for robotics"
    license = "BSD-2-Clause"
    homepage = "https://github.com/stack-of-tasks/dynamic-graph"
    topics = ("robotics", "data-flow", "graph", "signals", "entities")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "boost/*:with_serialization": True,
        "boost/*:with_thread": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.71]", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 3.1)",
                        "cmake_minimum_required(VERSION 3.5)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
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
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "dynamic-graph")

        self.cpp_info.components["core"].set_property("cmake_target_name", "dynamic-graph::dynamic-graph")
        self.cpp_info.components["core"].set_property("pkg_config_name", "dynamic-graph")
        self.cpp_info.components["core"].set_property("pkg_config_custom_content", "plugindir=lib/dynamic-graph-plugins")
        self.cpp_info.components["core"].libs = ["dynamic-graph"]
        self.cpp_info.components["core"].requires = [
            "boost::serialization",
            "boost::thread",
            "eigen::eigen"
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["core"].system_libs = ["m", "dl", "pthread"]

        self.cpp_info.components["tracer"].set_property("cmake_target_name", "dynamic-graph::tracer")
        self.cpp_info.components["tracer"].libdirs = ["lib/dynamic-graph-plugins"]
        self.cpp_info.components["tracer"].libs = ["tracer"]
        self.cpp_info.components["tracer"].requires = ["core"]

        self.cpp_info.components["tracer-real-time"].set_property("cmake_target_name", "dynamic-graph::tracer-real-time")
        self.cpp_info.components["tracer-real-time"].libdirs = ["lib/dynamic-graph-plugins"]
        self.cpp_info.components["tracer-real-time"].libs = ["tracer-real-time"]
        self.cpp_info.components["tracer-real-time"].requires = ["core", "tracer"]
