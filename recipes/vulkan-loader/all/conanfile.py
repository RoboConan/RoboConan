import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class VulkanLoaderConan(ConanFile):
    name = "vulkan-loader"
    description = "Khronos official Vulkan ICD desktop loader for Windows, Linux, and MacOS."
    topics = ("vulkan", "loader", "desktop", "gpu")
    homepage = "https://github.com/KhronosGroup/Vulkan-Loader"
    license = "Apache-2.0 AND MIT AND HPND-Kevlin-Henney"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_xcb": [True, False],
        "with_xlib": [True, False],
        "with_xrandr": [True, False],
        "with_wayland": [True, False],
        "with_directfb": [True, False],
    }
    default_options = {
        "with_xcb": True,
        "with_xlib": True,
        "with_xrandr": True,
        "with_wayland": True,
        "with_directfb": False,
    }
    languages = ["C"]

    @property
    def _is_mingw(self):
        return self.settings.os == "Windows" and self.settings.compiler == "gcc"

    @property
    def _is_pkgconf_needed(self):
        return self.options.get_safe("with_xcb") or self.options.get_safe("with_xlib") or \
               self.options.get_safe("with_wayland") or self.options.get_safe("with_directfb")

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_xcb
            del self.options.with_xlib
            del self.options.with_xrandr
            del self.options.with_wayland
            del self.options.with_directfb

    def configure(self):
        if not self.options.get_safe("with_xlib"):
            self.options.rm_safe("with_xrandr")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"vulkan-headers/[^{self.version}]", transitive_headers=True)
        if self.options.get_safe("with_xcb") or self.options.get_safe("with_xlib"):
            self.requires("xorg/system", visible=False)
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22.0]", visible=False)
        if self.options.get_safe("with_directfb"):
            self.requires("directfb/[^1.7.7]", visible=False)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.17.2 <5]")
        if self._is_pkgconf_needed:
            if not self.conf.get("tools.gnu:pkg_config", check_type=str):
                self.tool_requires("pkgconf/[<4]")
        if self._is_mingw:
            self.tool_requires("jwasm/2.13")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Honor settings.compiler.runtime
        if Version(self.version) < "1.3.254":
            replace_in_file(self, os.path.join(self.source_folder, "loader", "CMakeLists.txt"),
                            'if(${configuration} MATCHES "/MD")',
                            "if(FALSE)")
        else:
            if Version(self.version) < "1.3.275":
                replace_in_file(self, "CMakeLists.txt",
                                'set(TESTS_STANDARD_CXX_PROPERTIES ${LOADER_STANDARD_CXX_PROPERTIES} MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")',
                                "set(TESTS_STANDARD_CXX_PROPERTIES ${LOADER_STANDARD_CXX_PROPERTIES})")
            replace_in_file(self, "CMakeLists.txt", 'set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")', "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["VULKAN_HEADERS_INSTALL_DIR"] = self.dependencies["vulkan-headers"].package_folder.replace("\\", "/")
        tc.variables["BUILD_TESTS"] = False
        tc.variables["USE_CCACHE"] = False
        if self.settings.os in ["Linux", "FreeBSD"]:
            tc.variables["BUILD_WSI_XCB_SUPPORT"] = self.options.with_xcb
            tc.variables["BUILD_WSI_XLIB_SUPPORT"] = self.options.with_xlib
            tc.variables["BUILD_WSI_XLIB_XRANDR_SUPPORT"] = self.options.get_safe("with_xrandr", False)
            tc.variables["BUILD_WSI_WAYLAND_SUPPORT"] = self.options.with_wayland
            tc.variables["BUILD_WSI_DIRECTFB_SUPPORT"] = self.options.with_directfb
        if self.settings.os == "Windows":
            tc.variables["ENABLE_WIN10_ONECORE"] = False
        tc.variables["BUILD_LOADER"] = True
        if self.settings.os == "Windows":
            tc.variables["USE_MASM"] = True
        tc.variables["ENABLE_WERROR"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        if self._is_pkgconf_needed:
            pkg = PkgConfigDeps(self)
            pkg.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.txt", src=os.path.join(self.source_folder, "LICENSES"), dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "loader"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_module_file_name", "Vulkan")
        self.cpp_info.set_property("cmake_file_name", "VulkanLoader")
        self.cpp_info.set_property("cmake_module_target_name", "Vulkan::Vulkan")
        self.cpp_info.set_property("cmake_target_name", "Vulkan::Loader")
        self.cpp_info.set_property("pkg_config_name", "vulkan")
        suffix = "-1" if self.settings.os == "Windows" else ""
        self.cpp_info.libs = [f"vulkan{suffix}"]

        # The version in the official CMake ConfigVersion.cmake has only three components: major.minor.patch
        # Vulkan interprets four-part version strings as variant.major.minor.patch, which
        # can unintentionally invalidate compatibility checks in consuming code.
        # https://registry.khronos.org/vulkan/specs/latest/html/vkspec.html#extendingvulkan-coreversions-versionnumbers
        # https://github.com/KhronosGroup/Vulkan-Loader/blob/vulkan-sdk-1.4.313.0/loader/loader.c#L2499-L2507
        three_part_version = self.version.rsplit(".", 1)[0]
        self.cpp_info.set_property("system_package_version", three_part_version)

        # allow to properly set Vulkan_INCLUDE_DIRS in FindVulkan.cmake
        self.cpp_info.includedirs = self.dependencies["vulkan-headers"].cpp_info.aggregated_components().includedirs

        self.cpp_info.requires.append("vulkan-headers::vulkan-headers")
