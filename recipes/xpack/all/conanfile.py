import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"

class XpackConan(ConanFile):
    name = "xpack"
    description = "C++ reflection, ability to convert between C++ structures and json/xml."
    license = "Apache-2.0"
    homepage = "https://github.com/xyz347/xpack"
    topics = ("json", "bson", "reflection", "xml", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("rapidjson/[>=0.0+git.20250205]")
        self.requires("rapidxml/1.13")

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(
            self,
            pattern="*.h",
            dst=os.path.join(self.package_folder, "include", "xpack"),
            src=self.source_folder,
            excludes=["example", "gtest", "thirdparty", "rapidjson"],
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
