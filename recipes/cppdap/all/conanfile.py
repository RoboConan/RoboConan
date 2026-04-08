import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class PackageConan(ConanFile):
    name = "cppdap"
    description = "Debug Adapter Protocol SDK"
    license = "Apache-2.0"
    homepage = "https://github.com/google/cppdap"
    topics = ("debug", "adapter", "protocol", "dap")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_json": ["jsoncpp", "nlohmann_json", "rapidjson"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_json": "nlohmann_json",
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_json == "jsoncpp":
            self.requires("jsoncpp/[^1.9.5]")
        elif self.options.with_json == "rapidjson":
            self.requires("rapidjson/[>=0.0+git.20250205]")
        elif self.options.with_json == "nlohmann_json":
            self.requires("nlohmann_json/[^3]")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.options.shared and is_msvc(self):
            raise ConanInvalidConfiguration(f"{self.ref} cannot be built as shared on Visual Studio and msvc.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CPPDAP_USE_EXTERNAL_JSONCPP_PACKAGE"] = self.options.with_json == "jsoncpp"
        tc.variables["CPPDAP_USE_EXTERNAL_RAPIDJSON_PACKAGE"] = self.options.with_json == "rapidjson"
        tc.variables["CPPDAP_USE_EXTERNAL_NLOHMANN_JSON_PACKAGE"] = self.options.with_json == "nlohmann_json"
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cppdap"]

        self.cpp_info.set_property("cmake_file_name", "cppdap")
        self.cpp_info.set_property("cmake_target_name", "cppdap::cppdap")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("pthread")
        if self.settings.os in ["Windows"]:
            self.cpp_info.system_libs.append("ws2_32")
