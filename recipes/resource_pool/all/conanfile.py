import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class ResourcePool(ConanFile):
    name = "resource_pool"
    description = "C++ header only library purposed to create pool of some resources like keepalive connections"
    license = "MIT"
    homepage = "http://github.com/elsid/resource_pool"
    topics = ("resource pool", "asio", "elsid", "c++17", "cpp17", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        self.options["boost"].with_coroutine = True
        self.options["boost"].with_thread = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Only compatible with Boost up to v1.79
        self.requires("boost/[^1.71.0 <1.80]")

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        copy(self, "*",
             dst=os.path.join(self.package_folder, "include", "yamail"),
             src=os.path.join(self.source_folder, "include", "yamail"))

    def package_info(self):
        # Set up for compatibility with existing cmake configuration:
        # https://github.com/elsid/resource_pool/blob/3ea1f95/examples/CMakeLists.txt#L6C34-L6C54
        self.cpp_info.set_property("cmake_target_name", "elsid::resource_pool")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.requires = ["boost::coroutine", "boost::thread"]
        self.cpp_info.defines = ["BOOST_ASIO_USE_TS_EXECUTOR_AS_DEFAULT"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("ws2_32")
