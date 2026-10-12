import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class HiredisConan(ConanFile):
    name = "hiredis"
    description = "Hiredis is a minimalistic C client library for the Redis database."
    license = "BSD-3-Clause"
    topics = ("hiredis", "redis", "client", "database")
    homepage = "https://github.com/redis/hiredis"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.compiler.rm_safe("libcxx")
        self.settings.compiler.rm_safe("cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_ssl:
            self.requires("openssl/[<5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Since 1.2.0, BUILD_SHARED_LIBS has been defined by option()
        if Version(self.version) >= "1.2.0":
            tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        if Version(self.version) <= "1.2.0":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.7" # CMake 4 support
        tc.cache_variables["ENABLE_SSL"] = self.options.with_ssl
        tc.cache_variables["DISABLE_TESTS"] = True
        tc.cache_variables["ENABLE_EXAMPLES"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "build"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "hiredis")
        self.cpp_info.set_property("pkg_config_name", "none")

        suffix = ""
        if Version(self.version) >= "1.1.0":
            if is_msvc(self) and not self.options.shared and Version(self.version) < "1.2.0":
                suffix += "_static"
            if self.settings.build_type == "Debug":
                suffix += "d"

        # hiredis
        self.cpp_info.components["hiredislib"].set_property("cmake_target_name", "hiredis::hiredis")
        self.cpp_info.components["hiredislib"].set_property("pkg_config_name", "hiredis")
        self.cpp_info.components["hiredislib"].libs = [f"hiredis{suffix}"]
        self.cpp_info.components["hiredislib"].defines = ["_FILE_OFFSET_BITS=64"]
        self.cpp_info.components["hiredislib"].includedirs.append("include/hiredis")
        if self.settings.os == "Windows":
            self.cpp_info.components["hiredislib"].system_libs = ["ws2_32"]

        # hiredis_ssl
        if self.options.with_ssl:
            self.cpp_info.components["hiredis_ssl"].set_property("cmake_target_name", "hiredis::hiredis_ssl")
            self.cpp_info.components["hiredis_ssl"].set_property("pkg_config_name", "hiredis_ssl")
            self.cpp_info.components["hiredis_ssl"].libs = [f"hiredis_ssl{suffix}"]
            self.cpp_info.components["hiredis_ssl"].requires = ["openssl::ssl"]
            if self.settings.os == "Windows":
                self.cpp_info.components["hiredis_ssl"].requires.append("hiredislib")
