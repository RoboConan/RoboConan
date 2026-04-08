import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class XXSDSSDSLLite(ConanFile):
    name = "xxsds-sdsl-lite"
    description = "SDSL - Succinct Data Structure Library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/xxsds/sdsl-lite"
    topics = ("sdsl", "succint", "data-structures", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    provides = "sdsl-lite"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sdsl-lite")
        self.cpp_info.set_property("cmake_target_name", "sdsl-lite::sdsl-lite")
        self.cpp_info.set_property("pkg_config_name", "sdsl-lite")

        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        if is_msvc(self):
            self.cpp_info.defines.append("MSVC_COMPILER")
