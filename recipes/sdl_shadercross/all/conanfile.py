import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, get, replace_in_file, rmdir
from conan.tools.microsoft import is_msvc


class SdlShadercrossConan(ConanFile):
    name = "sdl_shadercross"
    description = "Shader translation library for SDL's GPU API"
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/SDL_shadercross"
    topics = ("sdl3", "shader", "spir-v", "hlsl", "msl", "gpu")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_executable": [True, False],
        "with_dxc": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_executable": True,
        "with_dxc": True,
        "spirv-cross/*:c_api": True,
    }
    implements = ["auto_shared_fpic"]
    languages = "C"

    def config_options(self):
        if self.settings.os not in ["Linux", "Windows"]:
            del self.options.with_dxc

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _is_clang_cl(self):
        return (self.settings.os == "Windows" and self.settings.compiler == "clang"
                and self.settings.compiler.get_safe("runtime"))

    def requirements(self):
        self.requires("sdl/[^3]", transitive_headers=True)
        self.requires("spirv-cross/[^1.4.350.0]")
        if self.options.get_safe("with_dxc"):
            self.requires("directx-shader-compiler/[^1.8]")
        if self.settings.os != "Windows":
            self.requires("vkd3d/[^2.0]", headers=False, libs=False, run=True)

    def validate(self):
        if self.options.shared and not self.dependencies["sdl"].options.shared:
            raise ConanInvalidConfiguration("A shared SDL_shadercross library requires a shared SDL library")

    def package_id(self):
        self.info.requires["spirv-cross"].full_package_mode()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        rmdir(self, os.path.join(self.source_folder, "external"))
        replace_in_file(self, "CMakeLists.txt",
            'set(DirectXShaderCompiler_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/external/DirectXShaderCompiler-binaries")\n'
            '\t\tfind_package(DirectXShaderCompiler REQUIRED)',
            "find_package(DirectXShaderCompiler REQUIRED CONFIG)")
        replace_in_file(self, "CMakeLists.txt",
            "\tset(CMAKE_OSX_DEPLOYMENT_TARGET 11.0)\n",
            "")

    @property
    def _spirv_cross_shared(self):
        return self.dependencies["spirv-cross"].options.shared

    def generate(self):
        VirtualRunEnv(self).generate(scope="build")

        tc = CMakeToolchain(self)
        tc.cache_variables["SDLSHADERCROSS_DXC"] = self.options.get_safe("with_dxc", False)
        tc.cache_variables["SDLSHADERCROSS_SHARED"] = self.options.shared
        tc.cache_variables["SDLSHADERCROSS_STATIC"] = not self.options.shared
        tc.cache_variables["SDLSHADERCROSS_SPIRVCROSS_SHARED"] = self._spirv_cross_shared
        tc.cache_variables["SDLSHADERCROSS_VENDORED"] = False
        tc.cache_variables["SDLSHADERCROSS_CLI"] = self.options.build_executable
        tc.cache_variables["SDLSHADERCROSS_CLI_STATIC"] = False
        tc.cache_variables["SDLSHADERCROSS_WERROR"] = False
        tc.cache_variables["SDLSHADERCROSS_INSTALL"] = True
        tc.cache_variables["SDLSHADERCROSS_INSTALL_CPACK"] = False
        tc.cache_variables["SDLSHADERCROSS_INSTALL_MAN"] = False
        tc.cache_variables["SDLSHADERCROSS_INSTALL_RUNTIME"] = False
        tc.cache_variables["SDLSHADERCROSS_TESTS"] = False
        tc.generate()

        deps = CMakeDeps(self)
        spirv_cross_config = "spirv_cross_c_shared" if self._spirv_cross_shared else "spirv_cross_c"
        deps.set_property("spirv-cross", "cmake_file_name", spirv_cross_config)
        if self.options.get_safe("with_dxc"):
            deps.set_property("directx-shader-compiler::dxcompiler", "cmake_target_name", "DirectXShaderCompiler::dxcompiler")
            deps.set_property("directx-shader-compiler::dxil", "cmake_target_name", "DirectXShaderCompiler::dxil")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SDL3_shadercross")
        self.cpp_info.set_property("cmake_target_name", "SDL3_shadercross::SDL3_shadercross")
        alias = "shared" if self.options.shared else "static"
        self.cpp_info.set_property("cmake_target_aliases", [f"SDL3_shadercross::SDL3_shadercross-{alias}"])
        self.cpp_info.set_property("pkg_config_name", "sdl3-shadercross")
        lib_suffix = "-static" if (is_msvc(self) or self._is_clang_cl) and not self.options.shared else ""
        self.cpp_info.libs = [f"SDL3_shadercross{lib_suffix}"]
        self.cpp_info.requires = [
            "sdl::sdl3",
            f"spirv-cross::spirv-cross-c{'-shared' if self._spirv_cross_shared else ''}",
        ]
        if self.options.get_safe("with_dxc"):
            self.cpp_info.requires.append("directx-shader-compiler::dxcompiler")
        if self.settings.os != "Windows":
            self.cpp_info.requires.append("vkd3d::utils")
