import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class VulkanValidationLayersConan(ConanFile):
    name = "vulkan-validationlayers"
    description = "Khronos official Vulkan validation layers for Windows, Linux, Android, and MacOS."
    license = "Apache-2.0"
    topics = ("vulkan", "validation-layers")
    homepage = "https://github.com/KhronosGroup/Vulkan-ValidationLayers"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "with_xcb": [True, False],
        "with_xlib": [True, False],
        "with_xrandr": [True, False],
        "with_wayland": [True, False],
        "with_mimalloc": [True, False],
    }
    default_options = {
        "fPIC": True,
        "with_xcb": True,
        "with_xlib": True,
        "with_xrandr": True,
        "with_wayland": True,
        "with_mimalloc": False,
    }

    @property
    def _needs_pkg_config(self):
        return self.options.get_safe("with_xcb") or \
               self.options.get_safe("with_xlib") or \
               self.options.get_safe("with_wayland")

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if Version(self.version) < "1.4.363":
            self.options.rm_safe("with_xrandr")
        if self.settings.os not in ["Linux", "FreeBSD"]:
            self.options.rm_safe("with_xcb")
            self.options.rm_safe("with_xlib")
            self.options.rm_safe("with_xrandr")
            self.options.rm_safe("with_wayland")
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            del self.options.with_mimalloc

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _vulkan_sdk_version(self):
        return self.version

    def requirements(self):
        self.requires(f"spirv-headers/{self._vulkan_sdk_version}")
        self.requires(f"spirv-tools/{self._vulkan_sdk_version}", visible=False)
        self.requires(f"vulkan-headers/{self._vulkan_sdk_version}", transitive_headers=True)
        if Version(self.version) >= "1.3.268.0":
            self.requires(f"vulkan-utility-libraries/{self._vulkan_sdk_version}")

        if Version(self.version) >= "1.4.313":
            self.requires("parallel-hashmap/[^2.0.0]")
        else:
            self.requires("robin-hood-hashing/3.11.5")
        if self.options.get_safe("with_xcb") or self.options.get_safe("with_xlib"):
            self.requires("xorg/system", libs=False)
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22.0]", libs=False)

        if self.options.get_safe("with_mimalloc"):
            self.requires("mimalloc/[>=2.2.4 <4]", options={"shared": False})

    def validate(self):
        check_min_cppstd(self, 17)
        if self.options.get_safe("with_xrandr") and not self.options.get_safe("with_xlib"):
            raise ConanInvalidConfiguration("Xrandr WSI support requires Xlib WSI support")

    def build_requirements(self):
        if self._needs_pkg_config and not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        self.tool_requires("cmake/[>=3.22.1 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["VVL_CLANG_TIDY"] = False
        tc.variables["USE_CCACHE"] = False
        if self.settings.os in ["Linux", "FreeBSD"]:
            tc.variables["BUILD_WSI_XCB_SUPPORT"] = self.options.get_safe("with_xcb")
            tc.variables["BUILD_WSI_XLIB_SUPPORT"] = self.options.get_safe("with_xlib")
            tc.variables["BUILD_WSI_XLIB_XRANDR_SUPPORT"] = self.options.get_safe("with_xrandr")
            tc.variables["BUILD_WSI_WAYLAND_SUPPORT"] = self.options.get_safe("with_wayland")
        elif self.settings.os == "Android":
            tc.variables["BUILD_WSI_XCB_SUPPORT"] = False
            tc.variables["BUILD_WSI_XLIB_SUPPORT"] = False
            tc.variables["BUILD_WSI_WAYLAND_SUPPORT"] = False
        tc.variables["BUILD_WERROR"] = False
        tc.variables["BUILD_TESTS"] = False
        tc.variables["INSTALL_TESTS"] = False
        tc.variables["BUILD_LAYERS"] = True
        tc.variables["BUILD_LAYER_SUPPORT_FILES"] = True
        tc.variables["VVL_CODEGEN"] = False
        tc.variables["UPDATE_DEPS"] = False
        if self.options.get_safe("with_mimalloc") is not None:
            tc.variables["USE_MIMALLOC"] = self.options.with_mimalloc
        if Version(self.version) >= "1.4.313":
            tc.variables["USE_CUSTOM_HASH_MAP"] = True
        else:
            tc.variables["USE_ROBIN_HOOD_HASHING"] = True
        # Suppress overly noisy warnings
        # tc.extra_cxxflags.append("-w")
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        if self._needs_pkg_config:
            deps = PkgConfigDeps(self)
            deps.generate()

    def _patch_sources(self):
        # FIXME: two CMake module/config files should be generated (SPIRV-ToolsConfig.cmake and SPIRV-Tools-optConfig.cmake),
        # but it can't be modeled right now in spirv-tools recipe
        if not os.path.exists(os.path.join(self.generators_folder, "SPIRV-Tools-optConfig.cmake")):
            shutil.copy(
                os.path.join(self.generators_folder, "SPIRV-ToolsConfig.cmake"),
                os.path.join(self.generators_folder, "SPIRV-Tools-optConfig.cmake"),
            )
        if self.settings.os == "Android":
            # INFO: libVkLayer_utils.a: error: undefined symbol: __android_log_print
            # https://github.com/KhronosGroup/Vulkan-ValidationLayers/commit/a26638ae9fdd8c40b56d4c7b72859a5b9a0952c9
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            "VkLayer_utils PUBLIC Vulkan::Headers", "VkLayer_utils PUBLIC Vulkan::Headers -landroid -llog")
        if not self.options.get_safe("fPIC"):
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            "CMAKE_POSITION_INDEPENDENT_CODE ON", "CMAKE_POSITION_INDEPENDENT_CODE OFF")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        if self.settings.os == "Windows":
            # import lib is useless, validation layers are loaded at runtime
            lib_dir = os.path.join(self.package_folder, "lib")
            rm(self, "VkLayer_khronos_validation.lib", lib_dir)
            rm(self, "libVkLayer_khronos_validation.dll.a", lib_dir)
            # move dll and json manifest files in bin folder
            bin_dir = os.path.join(self.package_folder, "bin")
            mkdir(self, bin_dir)
            for ext in ("*.dll", "*.json"):
                for bin_file in glob.glob(os.path.join(lib_dir, ext)):
                    shutil.move(bin_file, os.path.join(bin_dir, os.path.basename(bin_file)))
        fix_apple_shared_install_name(self)

    def package_info(self):
        # The output of the package is a VkLayer_khronos_validation runtime library.

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        if self.settings.os != "Windows":
            self.cpp_info.bindirs = ["lib"]

        if self.settings.os == "Windows":
            manifest_dir = "bin"
        else:
            manifest_dir = os.path.join("share", "vulkan", "explicit_layer.d")
        self.runenv_info.append_path("VK_LAYER_PATH", os.path.join(self.package_folder, manifest_dir))

        # The version in the official CMake ConfigVersion.cmake has only three components: major.minor.patch
        # Vulkan interprets four-part version strings as variant.major.minor.patch, which
        # can unintentionally invalidate compatibility checks in consuming code.
        three_part_version = self.version.rsplit(".", 1)[0]
        self.cpp_info.set_property("system_package_version", three_part_version)
