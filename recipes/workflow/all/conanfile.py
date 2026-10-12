import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class WorkflowConan(ConanFile):
    name = "workflow"
    description = "C++ Parallel Computing and Asynchronous Networking Framework"
    license = "Apache-2.0"
    homepage = "https://github.com/sogou/workflow"
    topics = ("async", "networking", "parallel-computing")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "kafka": [True, False],
        "mysql": [True, False],
        "redis": [True, False],
        "consul": [True, False],
        "upstream": [True, False],
    }

    default_options = {
        "shared": False,
        "fPIC": True,
        "kafka": True,
        "mysql": True,
        "redis": True,
        "consul": True,
        "upstream": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/[<5]", transitive_headers=True)
        if self.options.kafka:
            self.requires("snappy/[^1.1]", transitive_headers=True)
            self.requires("lz4/[^1.9]")
            self.requires("zstd/[^1.5]")
            self.requires("zlib-ng/[^2]")

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["KAFKA"] = "y" if self.options.kafka else "n"
        tc.cache_variables["MYSQL"] = "y" if self.options.mysql else "n"
        tc.cache_variables["REDIS"] = "y" if self.options.redis else "n"
        tc.cache_variables["CONSUL"] = "y" if self.options.consul else "n"
        tc.cache_variables["UPSTREAM"] = "y" if self.options.upstream else "n"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("lz4", "cmake_target_name", "lz4::lz4")
        deps.set_property("zstd", "cmake_target_name", "zstd::zstd")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
            rm(self, "*.lib", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*.dll", os.path.join(self.package_folder, "bin"))
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))
            rm(self, "*.dylib", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "workflow")
        self.cpp_info.components["workflow_"].set_property("cmake_target_name", "workflow")
        self.cpp_info.components["workflow_"].libs = ["workflow"]
        self.cpp_info.components["workflow_"].requires = ["openssl::openssl"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["workflow_"].system_libs = ["pthread", "rt"]

        if self.options.kafka:
            self.cpp_info.components["wfkafka"].set_property("cmake_target_name", "wfkafka")
            self.cpp_info.components["wfkafka"].libs = ["wfkafka"]
            self.cpp_info.components["wfkafka"].requires = ["workflow_", "snappy::snappy", "lz4::lz4", "zstd::zstd", "zlib-ng::zlib-ng"]
