import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class DirectXHeadersConan(ConanFile):
    name = "directx-headers"
    description = "Headers for using D3D12"
    license = "MIT"
    homepage = "https://github.com/microsoft/DirectX-Headers"
    topics = ("3d", "d3d", "d3d12", "direct", "direct3d", "directx", "graphics")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.name} is not supported on {self.settings.os}")
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 14)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["DXHEADERS_BUILD_TEST"] = False
        tc.cache_variables["DXHEADERS_BUILD_GOOGLE_TEST"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "directx-headers")
        self.cpp_info.set_property("pkg_config_name", "DirectX-Headers")

        self.cpp_info.components["headers"].set_property("cmake_target_name", "Microsoft::DirectX-Headers")
        if Version(self.version) >= "1.610.2":
            self.cpp_info.components["headers"].libs = ["DirectX-Headers"]
        if self.settings.os == "Linux" or self.settings.get_safe("os.subsystem") == "wsl":
            self.cpp_info.components["headers"].includedirs.append("include/wsl/stubs")
        if self.settings.os == "Windows":
            self.cpp_info.components["headers"].system_libs.append("d3d12")
            if self.settings.compiler == "msvc":
                self.cpp_info.components["headers"].system_libs.append("dxcore")

        self.cpp_info.components["guids"].set_property("cmake_target_name", "Microsoft::DirectX-Guids")
        self.cpp_info.components["guids"].libs = ["DirectX-Guids"]
        self.cpp_info.components["guids"].requires = ["headers"]
