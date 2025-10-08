import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import *

required_conan_version = ">=2.1"


class CcacheConan(ConanFile):
    name = "ccache"
    description = (
        "Ccache (or “ccache”) is a compiler cache. It speeds up recompilation "
        "by caching previous compilations and detecting when the same "
        "compilation is being done again."
    )
    license = "GPL-3.0-or-later"
    homepage = "https://ccache.dev"
    topics = ("compiler-cache", "recompilation", "cache", "compiler")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "redis_storage_backend": [True, False],
    }
    default_options = {
        "redis_storage_backend": True,
    }

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zstd/[>=1.5 <1.6]")
        self.requires("fmt/[>=10]")
        self.requires("xxhash/[>=0.8.1 <0.9]")
        if self.options.redis_storage_backend:
            self.requires("hiredis/[^1.0]")

    def validate(self):
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["REDIS_STORAGE_BACKEND"] = self.options.redis_storage_backend
        tc.variables["HIREDIS_FROM_INTERNET"] = False
        tc.variables["ZSTD_FROM_INTERNET"] = False
        tc.variables["ENABLE_DOCUMENTATION"] = False
        tc.variables["ENABLE_TESTING"] = False
        tc.variables["STATIC_LINK"] = False  # Don't link static runtimes and let Conan handle it
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("fmt", "cmake_file_name", "Fmt")
        deps.set_property("fmt", "cmake_find_mode", "module")
        deps.set_property("fmt", "cmake_target_name", "dep_fmt")
        deps.set_property("zstd", "cmake_file_name", "Zstd")
        deps.set_property("zstd", "cmake_target_name", "dep_zstd")
        deps.set_property("hiredis", "cmake_file_name", "Hiredis")
        deps.set_property("hiredis", "cmake_target_name", "dep_hiredis")
        deps.set_property("zstd", "cmake_find_mode", "module")
        deps.set_property("hiredis", "cmake_find_mode", "module")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "*GPL-*.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
