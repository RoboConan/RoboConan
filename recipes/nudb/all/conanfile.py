import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class NudbConan(ConanFile):
    name = "nudb"
    description = "A fast key/value insert-only database for SSD drives in C++11"
    license = "BSL-1.0"
    homepage = "https://github.com/CPPAlliance/NuDB"
    topics = ("header-only", "KVS", "insert-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.71.0]", options={"with_thread": True})

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE*",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        copy(self, "*",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.set_property("cmake_target_name", "NuDB")
        self.cpp_info.set_property("cmake_target_aliases", ["NuDB::nudb"])
        self.cpp_info.set_property("cmake_find_mode", "both")

        self.cpp_info.components["core"].set_property("cmake_target_name", "nudb")
        self.cpp_info.components["core"].requires = ["boost::thread"]
