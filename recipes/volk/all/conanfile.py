import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class VolkConan(ConanFile):
    name = "volk"
    license = "MIT"
    homepage = "https://github.com/zeux/volk"
    description = (
        "volk is a meta-loader for Vulkan. It allows you to dynamically load "
        "entrypoints required to use Vulkan without linking to vulkan-1.dll or "
        "statically linking Vulkan loader. Additionally, volk simplifies the "
        "use of Vulkan extensions by automatically loading all associated "
        "entrypoints. Finally, volk enables loading Vulkan entrypoints "
        "directly from the driver which can increase performance by skipping "
        "loader dispatch overhead."
    )
    topics = ("vulkan", "loader", "extension", "entrypoint", "graphics")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "namespace": [True, False],
    }
    default_options = {
        "fPIC": True,
        "namespace": False,
    }
    options_description = {
        "namespace": "Places the Vulkan function pointers in the volk C++ namespace",
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if Version(self.version) < "1.4.363":
            del self.options.namespace

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"vulkan-headers/[^{self.version}]", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        if Version(self.version) >= "1.4.363":
            replace_in_file(self, "CMakeLists.txt",
                            "  if(VOLK_NAMESPACE)\n    target_compile_definitions",
                            "  if(VOLK_NAMESPACE)\n    enable_language(CXX)\n    target_compile_definitions")
            return
        if Version(self.version) >= "1.3.296":
            replace_in_file(self, "CMakeLists.txt",
                            "if(VULKAN_HEADERS_INSTALL_DIR)",
                            "if(1)\nfind_package(VulkanHeaders REQUIRED)\nset(VOLK_INCLUDES ${VulkanHeaders_INCLUDE_DIRS})\nelseif(VULKAN_HEADERS_INSTALL_DIR)")
        else:
            replace_in_file(self, "CMakeLists.txt",
                            "if(VULKAN_HEADERS_INSTALL_DIR)",
                            "if(1)\nset(VOLK_INCLUDES ${VulkanHeaders_INCLUDE_DIRS})\nelseif(VULKAN_HEADERS_INSTALL_DIR)")
            replace_in_file(self, "CMakeLists.txt",
                            "find_package(Vulkan QUIET)",
                            "find_package(VulkanHeaders REQUIRED)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["VOLK_PULL_IN_VULKAN"] = True
        tc.variables["VOLK_INSTALL"] = True
        tc.variables["VOLK_NAMESPACE"] = self.options.get_safe("namespace", False)
        if Version(self.version) >= "1.4.363":
            tc.variables["VULKAN_HEADERS_INSTALL_DIR"] = self.dependencies["vulkan-headers"].package_folder
        if Version(self.version) < "1.3.270":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "volk")

        self.cpp_info.components["libvolk"].set_property("cmake_target_name", "volk::volk")
        self.cpp_info.components["libvolk"].libs = ["volk"]
        self.cpp_info.components["libvolk"].requires = ["vulkan-headers::vulkan-headers"]
        if self.options.get_safe("namespace"):
            self.cpp_info.components["libvolk"].defines = ["VOLK_NAMESPACE"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libvolk"].system_libs = ["dl"]

        self.cpp_info.components["volk_headers"].set_property("cmake_target_name", "volk::volk_headers")
        self.cpp_info.components["volk_headers"].libs = []
        self.cpp_info.components["volk_headers"].requires = ["vulkan-headers::vulkan-headers"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["volk_headers"].system_libs = ["dl"]

        # The version in volkConfigVersion.cmake is just the patch part
        self.cpp_info.set_property("system_package_version", Version(self.version).patch)
