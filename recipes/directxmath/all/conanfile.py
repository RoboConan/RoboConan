import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class DirectXMathConan(ConanFile):
    name = "directxmath"
    description = "DirectXMath is an all inline SIMD C++ linear algebra library for use in games and graphics apps"
    license = "MIT"
    homepage = "https://github.com/microsoft/DirectXMath"
    topics = ("math", "simd", "directx", "graphics", "gamedev")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "build_xdsp": [True, False],
        "build_shmath": [True, False],
        "build_dx11": [True, False],
        "build_dx12": [True, False],
    }
    default_options = {
        "build_xdsp": False,
        "build_shmath": False,
        "build_dx11": False,
        "build_dx12": False,
    }

    def config_options(self):
        if self.settings.os != "Windows":
            self.options.rm_safe("build_dx11")
            self.options.rm_safe("build_dx12")

    def configure(self):
        if not self.options.build_shmath:
            self.package_type = "header-library"
            self.options.rm_safe("build_dx11")
            self.options.rm_safe("build_dx12")

    def package_id(self):
        if not self.info.options.build_shmath:
            self.info.settings.clear()

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("build_dx12"):
            self.requires("directx-headers/[^1]")

    def validate(self):
        if self.options.build_xdsp and self.settings.os != "Windows":
            # XDSP tries to use non-portable memcpy_s
            raise ConanInvalidConfiguration("XDSP is only supported on Windows")
        if self.options.build_shmath:
            check_min_cppstd(self, 17)
        else:
            check_min_cppstd(self, 11)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.21 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["sources"], strip_root=True)
        download(self, **self.conan_data["sources"][self.version]["sal.h"], filename="Inc/sal.h")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_XDSP"] = self.options.build_xdsp
        tc.cache_variables["BUILD_SHMATH"] = self.options.build_shmath
        if self.options.build_shmath:
            tc.cache_variables["BUILD_DX11"] = self.options.get_safe("build_dx11", False)
            tc.cache_variables["BUILD_DX12"] = self.options.get_safe("build_dx12", False)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "sal.h", os.path.join(self.source_folder, "Inc"), os.path.join(self.package_folder, "include"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "directxmath")
        self.cpp_info.set_property("cmake_config_version_compat", "AnyNewerVersion")

        directxmath = self.cpp_info.components["directxmath"]
        directxmath.set_property("cmake_target_name", "Microsoft::DirectXMath")
        directxmath.set_property("pkg_config_name", "DirectXMath")

        if self.options.build_xdsp:
            xdsp = self.cpp_info.components["xdsp"]
            xdsp.set_property("cmake_target_name", "Microsoft::XDSP")
            xdsp.requires = ["directxmath"]

        if self.options.build_shmath:
            directxsh = self.cpp_info.components["directxsh"]
            directxsh.set_property("cmake_target_name", "Microsoft::DirectXSH")
            directxsh.libs = ["DirectXSH"]
            directxsh.requires = ["directxmath"]
            if self.options.get_safe("build_dx12"):
                directxsh.requires.append("directx-headers::headers")
