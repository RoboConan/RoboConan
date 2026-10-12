import os
import re
from pathlib import Path

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class RestbedConan(ConanFile):
    name = "restbed"
    homepage = "https://github.com/Corvusoft/restbed"
    description = "Corvusoft's Restbed framework brings asynchronous RESTful functionality to C++14 applications."
    topics = ("restful", "server", "client", "json", "http", "ssl", "tls")
    license = "AGPL-3.0-or-later", "LicenseRef-CPL"  # Corvusoft Permissive License (CPL)
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "ipc": [True, False],
        "with_openssl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "ipc": False,
        "with_openssl": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.ipc

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("asio/[^1.27.0]")
        if self.options.with_openssl:
            self.requires("openssl/[<5]")

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # CMake v4 support
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required( VERSION 3.1.0 FATAL_ERROR )",
                        "cmake_minimum_required( VERSION 3.5 )")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_SSL"] = self.options.with_openssl
        tc.variables["BUILD_IPC"] = self.options.get_safe("ipc", False)
        tc.extra_cxxflags.append("-Wno-narrowing")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        if not self.options.shared:
            for file in list(Path(self.source_folder).rglob("*.h")) + list(Path(self.source_folder).rglob("*.hpp")):
                data = file.read_text()
                data = re.sub(r"__declspec\((dllexport|dllimport)\)", "", data)
                file.write_text(data)

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        libname = "restbed"
        if self.settings.os in ("Windows", ) and self.options.shared:
            libname += "-shared"
        self.cpp_info.libs = [libname]

        if self.settings.os in ("FreeBSD", "Linux", ):
            self.cpp_info.system_libs.extend(["dl", "m"])
        elif self.settings.os in ("Windows", ):
            self.cpp_info.system_libs.append("mswsock")
