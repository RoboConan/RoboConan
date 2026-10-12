import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.0"


class VulkanExtensionLayerConan(ConanFile):
    name = "vulkan-extensionlayer"
    description = "Layer providing Vulkan features when native support is unavailable"
    license = "Apache-2.0"
    homepage = "https://github.com/KhronosGroup/Vulkan-ExtensionLayer"
    topics = ("vulkan", "gpu")
    package_type = "application"  # only exports dynamically-linked libraries
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_xcb": [True, False],
        "with_xlib": [True, False],
        "with_wayland": [True, False],
    }
    default_options = {
        "with_xcb": True,
        "with_xlib": True,
        "with_wayland": True,
    }

    def config_options(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            self.options.rm_safe("with_xcb")
            self.options.rm_safe("with_xlib")
            self.options.rm_safe("with_wayland")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"vulkan-headers/{self.version}")
        self.requires(f"vulkan-utility-libraries/{self.version}")
        if self.options.get_safe("with_xcb") or self.options.get_safe("with_xlib"):
            self.requires("xorg/system", libs=False)
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22.0]", libs=False)

    def validate(self):
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22.1 <5]")
        if any(self.options.get_safe(option) for option in (
            "with_xcb", "with_xlib", "with_wayland"
        )) and not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_POSITION_INDEPENDENT_CODE ON)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_WERROR"] = False
        tc.variables["UPDATE_DEPS"] = False
        if self.settings.os in ["Linux", "FreeBSD"]:
            tc.variables["BUILD_WSI_XCB_SUPPORT"] = self.options.with_xcb
            tc.variables["BUILD_WSI_XLIB_SUPPORT"] = self.options.with_xlib
            tc.variables["BUILD_WSI_WAYLAND_SUPPORT"] = self.options.with_wayland
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

        if any(self.options.get_safe(option) for option in (
            "with_xcb", "with_xlib", "with_wayland"
        )):
            deps = PkgConfigDeps(self)
            deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "*", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        # Look for dynamically-linked libraries here
        if self.settings.os != "Windows":
            self.cpp_info.bindirs = ["lib"]

        if self.settings.os == "Windows":
            manifest_dir = "bin"
        else:
            manifest_dir = os.path.join("share", "vulkan", "explicit_layer.d")
        self.runenv_info.append_path("VK_LAYER_PATH", os.path.join(self.package_folder, manifest_dir))

        three_part_version = self.version.rsplit(".", 1)[0]
        self.cpp_info.set_property("system_package_version", three_part_version)
