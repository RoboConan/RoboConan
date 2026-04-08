import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class JsonDtoConan(ConanFile):
    name = "json_dto"
    description = "A small header-only helper for converting data between json representation and c++ structs"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Stiffstream/json_dto"
    topics = ("json", "dto", "serialization", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("rapidjson/[>=0.0+git.20250205]")

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 14)
        # several gcc doesn't allow "this" in noexcept clauses due to bug. https://gcc.gnu.org/bugzilla/show_bug.cgi?id=100752
        if Version(self.version) >= "0.3.2" and \
            self.settings.compiler == "gcc" and \
            (Version(self.settings.compiler.version) < "9.0" or Version(self.settings.compiler.version).major == 11):
            raise ConanInvalidConfiguration(f"{self.ref} requires gcc 9, 10 or 12 later")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(
            self,
            pattern="*.hpp",
            dst=os.path.join(self.package_folder, "include", "json_dto"),
            src=os.path.join(self.source_folder, "dev", "json_dto"),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.set_property("cmake_file_name", "json-dto")
        self.cpp_info.set_property("cmake_target_name", "json-dto::json-dto")
