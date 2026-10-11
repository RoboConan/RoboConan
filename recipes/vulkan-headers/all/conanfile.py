import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMake
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class VulkanHeadersConan(ConanFile):
    name = "vulkan-headers"
    description = "Vulkan Header files."
    license = "Apache-2.0 OR MIT"
    topics = ("vulkan-headers", "vulkan")
    homepage = "https://github.com/KhronosGroup/Vulkan-Headers"
    package_type = "header-library"
    package_id_embed_mode = "patch_mode"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    options = {
        "module": [True, False],
        "module_std": [True, False],
    }
    default_options = {
        "module": False,
        "module_std": False,
    }
    options_description = {
        "module": "Enables building of the Vulkan-Hpp C++ named module",
        "module_std": "Enables import std in the Vulkan-Hpp C++ named module",
    }

    # CMake 4.4's opt-in token from Help/dev/experimental.rst.
    _cmake_import_std_uuid = "f35a9ac6-8463-4d38-8eec-5d6008153e7d"

    def config_options(self):
        if Version(self.version) < "1.3.289":
            del self.options.module
        if Version(self.version) < "1.4.311" or Version(self.version) >= "1.4.363":
            del self.options.module_std

    def configure(self):
        if not self.options.get_safe("module"):
            self.options.rm_safe("module_std")

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.settings.clear()

    def validate(self):
        if self.options.get_safe("module"):
            check_min_cppstd(self, 23 if Version(self.version) >= "1.4.363" else 20)
        if self.options.get_safe("module_std"):
            check_min_cppstd(self, 23)

    def validate_build(self):
        if self.options.get_safe("module"):
            compiler_version = Version(self.settings.compiler.version)
            if Version(self.version) >= "1.4.363":
                if self.settings.compiler == "msvc" and compiler_version < "193":
                    raise ConanInvalidConfiguration("Module support requires MSVC 19.36 or higher")
                if self.settings.compiler == "clang" and compiler_version < "18.1.2":
                    raise ConanInvalidConfiguration("Module support requires Clang 18.1.2 or higher")
                if self.settings.compiler == "gcc" and compiler_version < "15":
                    raise ConanInvalidConfiguration("Module support requires GCC 15 or higher")
                if self.settings.compiler not in ["msvc", "clang", "gcc"]:
                    raise ConanInvalidConfiguration("The compiler does not support C++23 import std modules")
            else:
                if self.settings.compiler == "msvc" and compiler_version < "194":
                    raise ConanInvalidConfiguration("Module support requires MSVC 19.41 or higher")
                if self.settings.compiler == "clang" and compiler_version < "16":
                    raise ConanInvalidConfiguration("Module support requires Clang 16.0 or higher")
                if self.settings.compiler == "gcc" and compiler_version < "14":
                    raise ConanInvalidConfiguration("Module support requires GCC 14.0 or higher")

    def build_requirements(self):
        if self.options.get_safe("module"):
            self.tool_requires("cmake/[~4.4.0]")
            self.tool_requires("ninja/[^1.11]")
        elif Version(self.version) >= "1.4.309.0":
            self.tool_requires("cmake/[>=3.22.1 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja" if self.options.get_safe("module") else None)
        tc.cache_variables["VULKAN_HEADERS_ENABLE_TESTS"] = False
        tc.cache_variables["VULKAN_HEADERS_ENABLE_MODULE"] = self.options.get_safe("module", False)
        if self.options.get_safe("module_std") is not None:
            tc.cache_variables["VULKAN_HEADERS_ENABLE_MODULE_STD"] = self.options.module_std
        if self.options.get_safe("module") and Version(self.version) >= "1.4.363":
            tc.cache_variables["CMAKE_EXPERIMENTAL_CXX_IMPORT_STD"] = self._cmake_import_std_uuid
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _module_build_file(self):
        return "lib/cmake/conan-official-vulkan-headers-module.cmake"

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.txt", src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.get_safe("module") and Version(self.version) >= "1.4.363":
            save(self, os.path.join(self.package_folder, self._module_build_file), textwrap.dedent("""\
                set(_conan_vulkan_headers_include_dir "${CMAKE_CURRENT_LIST_DIR}/../../include")
                target_sources(Vulkan::HppModule INTERFACE
                    FILE_SET CXX_MODULES
                    BASE_DIRS "${_conan_vulkan_headers_include_dir}"
                    FILES
                        "${_conan_vulkan_headers_include_dir}/vulkan/vulkan.cppm"
                        "${_conan_vulkan_headers_include_dir}/vulkan/vulkan_video.cppm"
                )
                target_compile_features(Vulkan::HppModule INTERFACE cxx_std_23)
                set_property(TARGET Vulkan::HppModule PROPERTY CXX_MODULE_STD ON)
                unset(_conan_vulkan_headers_include_dir)
                """))
        # rmdir(self, os.path.join(self.package_folder, "share", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "VulkanHeaders")

        # The version in the official CMake ConfigVersion.cmake has only three components: major.minor.patch
        # Vulkan interprets four-part version strings as variant.major.minor.patch, which
        # can unintentionally invalidate compatibility checks in consuming code.
        # https://registry.khronos.org/vulkan/specs/latest/html/vkspec.html#extendingvulkan-coreversions-versionnumbers
        # https://github.com/KhronosGroup/Vulkan-Loader/blob/vulkan-sdk-1.4.313.0/loader/loader.c#L2499-L2507
        three_part_version = self.version.rsplit(".", 1)[0]
        self.cpp_info.set_property("system_package_version", three_part_version)

        self.cpp_info.components["vulkanheaders"].set_property("cmake_target_name", "Vulkan::Headers")
        self.cpp_info.components["vulkanheaders"].bindirs = []
        self.cpp_info.components["vulkanheaders"].libdirs = []

        self.cpp_info.components["vulkanregistry"].set_property("cmake_target_name", "Vulkan::Registry")
        self.cpp_info.components["vulkanregistry"].includedirs = [os.path.join("share", "vulkan", "registry")]
        self.cpp_info.components["vulkanregistry"].bindirs = []
        self.cpp_info.components["vulkanregistry"].libdirs = []
        self.cpp_info.components["vulkanregistry"].resdirs = ["share"]

        if self.options.get_safe("module"):
            #   target_sources(Vulkan::HppModule
            #     INTERFACE
            #       FILE_SET "module"
            #       TYPE "CXX_MODULES"
            #       BASE_DIRS "<package_folder>"
            #       FILES "<package_folder>/include/vulkan/vulkan.cppm"
            #   )
            self.cpp_info.components["hppmodule"].set_property("cmake_target_name", "Vulkan::HppModule")
            self.cpp_info.components["hppmodule"].requires = ["vulkanheaders"]
            if Version(self.version) >= "1.4.363":
                self.cpp_info.set_property("cmake_build_modules", [self._module_build_file])
