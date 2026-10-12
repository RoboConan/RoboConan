import os
from functools import cached_property

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class NppConan(ConanFile):
    name = "npp"
    description = "NPP: NVIDIA 2D Image and Signal Processing Performance Primitives libraries"
    license = "DocumentRef-LICENSE:LicenseRef-NVIDIA-CUDA-Toolkit-EULA"
    homepage = "https://docs.nvidia.com/cuda/npp/"
    topics = ("cuda", "image-processing", "signal-processing", "performance-primitives")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "cmake_alias": [True, False],
        "use_stubs": [True, False],
    }
    default_options = {
        "shared": False,
        "cmake_alias": True,
        "use_stubs": False,
    }

    python_requires = "conan-cuda/latest"

    @cached_property
    def cuda(self):
        return self.python_requires["conan-cuda"].module.Interface(self, enable_private=True)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.shared
            del self.options.use_stubs
            self.package_type = "shared-library"

    def configure(self):
        if not self.options.get_safe("shared", True):
            self.options.rm_safe("use_stubs")

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type
        del self.info.settings.cuda.architectures
        self.info.settings.cuda.version = self.cuda.major
        self.info.options.rm_safe("cmake_alias")
        self.info.options.rm_safe("use_stubs")

    def requirements(self):
        self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)
        if self.settings.os == "Linux" and not self.options.shared:
            self.cuda.requires("culibos")

    def validate(self):
        self.cuda.validate_package("libnpp")

    def build(self):
        self.cuda.download_package("libnpp")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        if self.settings.os == "Linux":
            if self.options.shared:
                copy(self, "*.so*", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
                copy(self, "*.so*", os.path.join(self.source_folder, "lib", "stubs"), os.path.join(self.package_folder, "lib", "stubs"))
            else:
                copy(self, "*_static.a", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
        else:
            bin_dir = os.path.join(self.source_folder, "bin", "x64") if self.cuda.major >= 13 else os.path.join(self.source_folder, "bin")
            lib_dir = os.path.join(self.source_folder, "lib", "x64")
            copy(self, "*.dll", bin_dir, os.path.join(self.package_folder, "bin"))
            copy(self, "*.lib", lib_dir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        suffix = "" if self.options.get_safe("shared", True) else "_static"
        alias_suffix = "_static" if self.options.get_safe("shared", True) else ""
        for name in [
            "nppc",    # Core
            "nppial",  # Image Analysis
            "nppicc",  # Image Color Conversion
            "nppidei", # Image Data Exchange and Initialization
            "nppif",   # Image Filtering
            "nppig",   # Image Geometry
            "nppim",   # Image Morphology
            "nppist",  # Image Statistics
            "nppisu",  # Image Signal Utilities
            "nppitc",  # Image Threshold and Compare
            "npps",    # Signal Processing
        ]:
            component = self.cpp_info.components[name]
            component.set_property("pkg_config_name", f"{name}-{self.cuda.version}")
            component.set_property("pkg_config_aliases", [name])  # unofficial
            component.set_property("component_version", str(self.cuda.version))
            component.set_property("cmake_target_name", f"CUDA::{name}{suffix}")
            if self.options.get_safe("cmake_alias"):
                component.set_property("cmake_target_aliases", [f"CUDA::{name}{alias_suffix}"])
            component.libs = [f"{name}{suffix}"]
            if self.options.get_safe("use_stubs"):
                component.libdirs = ["lib/stubs", "lib"]
            component.requires = ["cudart::cudart_"]
            if name != "nppc":
                component.requires.append("nppc")
            if self.settings.os == "Linux" and not self.options.shared:
                component.system_libs = ["rt", "pthread", "m", "dl", "gcc_s", "stdc++"]
                component.requires.append("culibos::culibos")

        # Unofficial aggregate target for Image Processing
        self.cpp_info.components["nppi"].set_property("pkg_config_name", f"nppi-{self.cuda.version}")
        self.cpp_info.components["nppi"].set_property("component_version", str(self.cuda.version))
        self.cpp_info.components["nppi"].set_property("cmake_target_name", f"CUDA::nppi{suffix}")
        if self.options.get_safe("cmake_alias"):
            self.cpp_info.components["nppi"].set_property("cmake_target_aliases", [f"CUDA::nppi{alias_suffix}"])
        self.cpp_info.components["nppi"].requires = ["nppial", "nppicc", "nppidei", "nppif", "nppig", "nppim", "nppist", "nppisu", "nppitc"]
