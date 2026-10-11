import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class VulkanUtilityLibrariesConan(ConanFile):
    name = "vulkan-utility-libraries"
    description = "Utility libraries for Vulkan developers"
    license = "Apache-2.0"
    topics = ("vulkan",)
    homepage = "https://github.com/KhronosGroup/Vulkan-Utility-Libraries"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"vulkan-headers/{self.version}", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22.1 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_POSITION_INDEPENDENT_CODE ON)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTS"] = False
        tc.variables["VUL_ENABLE_INSTALL"] = True
        tc.variables["VUL_WERROR"] = False
        tc.variables["UPDATE_DEPS"] = False
        if Version(self.version) >= "1.4.363":
            tc.variables["VUL_CODEGEN"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "LICENSES"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    @property
    def _exported_defines(self):
        # https://github.com/KhronosGroup/Vulkan-Utility-Libraries/blob/vulkan-sdk-1.3.268.0/src/CMakeLists.txt#L42-L56
        defines = ["VK_ENABLE_BETA_EXTENSIONS"]
        if self.settings.os == "Windows":
            defines += [
                "NOMINMAX",
                "WIN32_LEAN_AND_MEAN",
                "VK_USE_PLATFORM_WIN32_KHR",
            ]
        elif self.settings.os == "Android":
            defines.append("VK_USE_PLATFORM_ANDROID_KHR")
        elif is_apple_os(self):
            defines.append("VK_USE_PLATFORM_METAL_EXT")
            if self.settings.os == "iOS":
                defines.append("VK_USE_PLATFORM_IOS_MVK")
            else:
                defines.append("VK_USE_PLATFORM_MACOS_MVK")
        return defines

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "VulkanUtilityLibraries")

        # The version in the official CMake ConfigVersion.cmake has only three components: major.minor.patch
        # Vulkan interprets four-part version strings as variant.major.minor.patch, which
        # can unintentionally invalidate compatibility checks in consuming code.
        three_part_version = self.version.rsplit(".", 1)[0]
        self.cpp_info.set_property("system_package_version", three_part_version)

        # Vulkan::UtilityHeaders
        self.cpp_info.components["utilityheaders"].set_property("cmake_target_name", "Vulkan::UtilityHeaders")
        self.cpp_info.components["utilityheaders"].requires = ["vulkan-headers::vulkanheaders"]
        self.cpp_info.components["utilityheaders"].libdirs = []
        self.cpp_info.components["utilityheaders"].bindirs = []

        # Vulkan::LayerSettings
        self.cpp_info.components["layersettings"].set_property("cmake_target_name", "Vulkan::LayerSettings")
        self.cpp_info.components["layersettings"].requires = ["vulkan-headers::vulkanheaders"]
        self.cpp_info.components["layersettings"].libs = ["VulkanLayerSettings"]
        self.cpp_info.components["layersettings"].bindirs = []

        # Vulkan::CompilerConfiguration
        if Version(self.version) >= "1.3.265":
            compiler_configuration = self.cpp_info.components["compilerconfiguration"]
            compiler_configuration.set_property("cmake_target_name", "Vulkan::CompilerConfiguration")
            compiler_configuration.defines = self._exported_defines
            compiler_configuration.includedirs = []
            compiler_configuration.libdirs = []
            compiler_configuration.bindirs = []

            if self.settings.compiler == "msvc":
                compiler_configuration.cxxflags = ["/W4", "/we5038", "/wd4324", "/permissive-"]
            else:
                compiler_configuration.cxxflags = [
                    "-Wpedantic", "-Wunreachable-code", "-Wunused-function", "-Wall",
                    "-Wextra", "-Wpointer-arith", "-Wextra-semi",
                ]
                if self.settings.compiler in ["clang", "apple-clang"]:
                    compiler_configuration.cxxflags.extend([
                        "-Wunreachable-code-return", "-Wconversion", "-Wimplicit-fallthrough",
                        "-Wstring-conversion",
                    ])

        # Vulkan::SafeStruct
        if Version(self.version) >= "1.3.282":
            self.cpp_info.components["safestruct"].set_property("cmake_target_name", "Vulkan::SafeStruct")
            self.cpp_info.components["safestruct"].requires = ["vulkan-headers::vulkanheaders", "utilityheaders"]
            self.cpp_info.components["safestruct"].libs = ["VulkanSafeStruct"]
            self.cpp_info.components["safestruct"].bindirs = []
