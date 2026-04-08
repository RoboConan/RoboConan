import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class TCSBankUconfigConan(ConanFile):
    name = "tcsbank-uconfig"
    description = "Lightweight, header-only, C++17 configuration library"
    license = "Apache-2.0"
    homepage = "https://github.com/Tinkoff/uconfig"
    topics = ("configuration", "env", "json", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_rapidjson": [True, False],
    }
    default_options = {
        "with_rapidjson": True,
    }
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_rapidjson:
            self.requires("rapidjson/[>=0.0+git.20250205]")

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
        copy(self, "*.h",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))
        copy(self, "*.ipp",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.set_property("cmake_file_name", "uconfig")
        self.cpp_info.set_property("cmake_target_name", "uconfig::uconfig")
        self.cpp_info.set_property("pkg_config_name", "uconfig")

        if self.options.with_rapidjson:
            self.cpp_info.defines = ["RAPIDJSON_HAS_STDSTRING=1"]
