import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=2.4"


class SheenBidiConan(ConanFile):
    name = "sheenbidi"
    description = "A sophisticated implementation of Unicode Bidirectional Algorithm"
    license = "Apache-2.0"
    homepage = "https://github.com/Tehreer/SheenBidi"
    topics = ("unicode", "bidi", "text-layout")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "experimental_text_api": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "experimental_text_api": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["SB_CONFIG_EXPERIMENTAL_TEXT_API"] = self.options.experimental_text_api
        tc.cache_variables["SB_CONFIG_UNITY"] = True
        tc.cache_variables["BUILD_GENERATOR"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["ENABLE_COVERAGE"] = False
        tc.cache_variables["ENABLE_ASAN"] = False
        tc.cache_variables["ENABLE_UBSAN"] = False
        tc.generate()

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

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SheenBidi")
        self.cpp_info.set_property("cmake_target_name", "SheenBidi::SheenBidi")
        self.cpp_info.set_property("pkg_config_name", "sheenbidi")
        self.cpp_info.libs = ["SheenBidi"]
        if self.options.experimental_text_api:
            self.cpp_info.defines.append("SB_CONFIG_EXPERIMENTAL_TEXT_API")
        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.defines.append("SB_CONFIG_DLL_IMPORT")
