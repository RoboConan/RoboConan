import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OpenclIcdLoaderConan(ConanFile):
    name = "opencl-icd-loader"
    description = "OpenCL ICD Loader."
    license = "Apache-2.0"
    topics = ("opencl", "khronos", "parallel", "icd-loader")
    homepage = "https://github.com/KhronosGroup/OpenCL-ICD-Loader"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "disable_openclon12": [True, False],
        "enable_opencl_layers": [True, False],
        "enable_loader_managed_dispatch": [True, False],
        "build_layerinfo": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "disable_openclon12": False,
        "enable_opencl_layers": True,
        "enable_loader_managed_dispatch": True,
        "build_layerinfo": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            if Version(self.version) >= "2023.02.06":
                self.options.rm_safe("disable_openclon12")
        else:
            self.options.rm_safe("disable_openclon12")
        if Version(self.version) < "2021.04.29":
            self.options.rm_safe("enable_opencl_layers")
        if Version(self.version) < "2023.02.06":
            self.options.rm_safe("build_layerinfo")
        if Version(self.version) < "2025.07.22":
            self.options.rm_safe("enable_loader_managed_dispatch")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.get_safe("enable_opencl_layers", False):
            self.options.rm_safe("build_layerinfo")
        if Version(self.version) >= "2026.05.29" and not self.options.shared:
            self.options.rm_safe("enable_loader_managed_dispatch")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"opencl-headers/{self.version}", transitive_headers=True)
        self.requires(f"opencl-clhpp-headers/{self.version}", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        opencl_headers_includedirs = self.dependencies["opencl-headers"].cpp_info.aggregated_components().includedirs
        tc.cache_variables["OPENCL_ICD_LOADER_HEADERS_DIR"] = ";".join(opencl_headers_includedirs)
        if is_msvc(self):
            tc.variables["USE_DYNAMIC_VCXX_RUNTIME"] = not is_msvc_static_runtime(self)
        tc.variables["OPENCL_ICD_LOADER_PIC"] = self.options.get_safe("fPIC", True)
        tc.variables["OPENCL_ICD_LOADER_BUILD_TESTING"] = False
        tc.variables["BUILD_TESTING"] = False
        if Version(self.version) >= "2021.04.29":
            tc.variables["ENABLE_OPENCL_LAYERS"] = self.options.enable_opencl_layers
        if Version(self.version) >= "2023.02.06":
            tc.variables["ENABLE_OPENCL_LAYERINFO"] = self.options.get_safe("build_layerinfo", False)
        if (Version(self.version) >= "2025.07.22"
                and self.options.get_safe("enable_loader_managed_dispatch") is not None):
            tc.variables["ENABLE_OPENCL_LOADER_MANAGED_DISPATCH"] = self.options.enable_loader_managed_dispatch
        if self.options.get_safe("disable_openclon12") is not None:
            tc.variables["OPENCL_ICD_LOADER_DISABLE_OPENCLON12"] = self.options.disable_openclon12
        if Version(self.version) < "2024.10.24": # pylint: disable=conan-condition-evals-to-constant
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_module_file_name", "OpenCL")
        self.cpp_info.set_property("cmake_file_name", "OpenCLICDLoader")
        self.cpp_info.set_property("cmake_target_name", "OpenCL::OpenCL")
        self.cpp_info.set_property("pkg_config_name", "OpenCL")
        self.cpp_info.includedirs = []
        self.cpp_info.libs = ["OpenCL"]
        self.cpp_info.requires = [
            "opencl-headers::opencl-headers",
            "opencl-clhpp-headers::opencl-clhpp-headers",
        ]
        if not self.options.shared:
            if self.settings.os == "Linux":
                self.cpp_info.system_libs = ["dl", "pthread"]
            elif self.settings.os == "FreeBSD":
                self.cpp_info.system_libs = ["pthread"]
            elif self.settings.os == "Android":
                self.cpp_info.system_libs = ["dl"]
            elif self.settings.os == "Windows":
                self.cpp_info.system_libs = ["cfgmgr32", "runtimeobject"]
