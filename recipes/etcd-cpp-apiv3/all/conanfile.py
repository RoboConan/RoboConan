import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"

class EtcdCppApiv3Conan(ConanFile):
    name = "etcd-cpp-apiv3"
    description = "C++ library for etcd's v3 client APIs, i.e., ETCDCTL_API=3."
    license = "BSD-3-Clause"
    homepage = "https://github.com/etcd-cpp-apiv3/etcd-cpp-apiv3"
    topics = ("etcd", "api", )

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
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/[<5]")
        self.requires("grpc/[^1.50.2]")
        self.requires("cpprestsdk/2.10.19", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 14)

    def build_requirements(self):
        self.tool_requires("grpc/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # For CMake v4 support
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required (VERSION 3.3 FATAL_ERROR)",
                        "cmake_minimum_required (VERSION 3.5)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["gRPC_VERSION"] = self.dependencies["grpc"].ref.version
        tc.variables["ETCD_CMAKE_CXX_STANDARD"] = self.settings.compiler.cppstd
        tc.variables["OpenSSL_DIR"] = self.dependencies["openssl"].package_folder.replace('\\', '/')
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["etcd-cpp-api"]
