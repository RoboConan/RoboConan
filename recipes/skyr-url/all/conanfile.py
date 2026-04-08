import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime, is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SkyrUrlConan(ConanFile):
    name = "skyr-url"
    description = "A C++ library that implements the WhatWG URL specification"
    license = "BSL-1.0"
    homepage = "https://cpp-netlib.github.io/url"
    topics = ("whatwg", "url", "parser")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_json": [True, False],
        "with_fs": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_json": True,
        "with_fs": True,
    }
    implements = ["auto_shared_fpic"]

    @property
    def _min_cppstd(self):
        return 17

    @property
    def _minimum_compilers_version(self):
        # https://github.com/cpp-netlib/url/tree/v1.12.0#requirements
        return {
            "msvc": "192",
            "gcc": "7",
            "clang": "6" if Version(self.version) <= "1.12.0" else "8",
            "apple-clang": "10",
        }

    def export_sources(self):
        copy(self, "CMakeLists.txt", src=self.recipe_folder, dst=self.export_sources_folder)
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("tl-expected/1.1.0", transitive_headers=True)
        self.requires("range-v3/[>=0.12.0 <1]", transitive_headers=True)
        if self.options.with_json:
            self.requires("nlohmann_json/[^3]")

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)
        min_version = self._minimum_compilers_version.get(str(self.settings.compiler))
        if not min_version:
            self.output.warn(f"{self.ref} recipe lacks information about the {self.settings.compiler} compiler support.")
        else:
            if Version(self.settings.compiler.version) < min_version:
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires C++17 support. "
                    f"The current compiler {self.settings.compiler} {self.settings.compiler.version} does not support it.")

        if self.options.with_fs and self.settings.compiler == "apple-clang":
            raise ConanInvalidConfiguration("apple-clang currently does not support with filesystem")
        if self.settings.compiler.get_safe("libcxx") == "libstdc++":
            raise ConanInvalidConfiguration(f"{self.ref} supports only libstdc++'s new ABI")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["skyr_BUILD_TESTS"] = False
        tc.variables["skyr_FULL_WARNINGS"] = False
        tc.variables["skyr_WARNINGS_AS_ERRORS"] = False
        tc.variables["skyr_ENABLE_JSON_FUNCTIONS"] = self.options.with_json
        tc.variables["skyr_ENABLE_FILESYSTEM_FUNCTIONS"] = self.options.with_fs
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        if is_msvc(self):
            tc.variables["skyr_USE_STATIC_CRT"] = is_msvc_static_runtime(self)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE_1_0.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "skyr-url")
        self.cpp_info.set_property("cmake_target_name", "skyr::skyr-url")

        self.cpp_info.components["url"].name = "skyr-url"
        self.cpp_info.components["url"].libs = ["skyr-urld" if self.settings.build_type == "Debug" else "skyr-url"]
        self.cpp_info.components["url"].requires = ["tl-expected::tl-expected", "range-v3::range-v3"]
        if self.options.with_json:
            self.cpp_info.components["url"].requires.append("nlohmann_json::nlohmann_json")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["url"].system_libs.append("m")
