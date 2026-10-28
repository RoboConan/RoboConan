import os
from functools import cached_property
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class IntelOpenCLConan(ConanFile):
    name = "intel-opencl"
    description = "Intel oneAPI OpenCL Runtime"
    # https://intel.ly/393CijO
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://www.intel.com/content/www/us/en/developer/tools/opencl/overview.html"
    topics = ("intel", "opencl", "pre-built")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    default_options = {
        "zlib-ng/*:shared": True,
    }

    provides = ["opencl-icd-loader"]

    @cached_property
    def _packages(self):
        with open(os.path.join(self.recipe_folder, "sources", f"{self.version}.yml")) as f:
            return yaml.safe_load(f)[str(self.settings.os)]

    def export(self):
        copy(self, f"{self.version}.yml", os.path.join(self.recipe_folder, "sources"), os.path.join(self.export_folder, "sources"))

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("opencl-headers/[*]", transitive_headers=True)
        version = ".".join(str(self.version).split(".")[:2])
        self.requires(f"intel-compiler-runtime/[~{version}]")
        if Version(self.version) < "2025":
            self.requires("onetbb/[^2021]")
        elif Version(self.version) < "2026":
            self.requires("onetbb/[^2022]")
        else:
            self.requires("onetbb/[^2023]")
        if self.settings.os == "Linux":
            self.requires("zlib-ng/[^2.0]")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(f"{self.settings.arch} is not supported")
        if self.settings.os == "Linux" and not self.dependencies["zlib-ng"].options.shared:
            raise ConanInvalidConfiguration("intel-opencl requires zlib-ng:shared=True")

    def _get_pypi_package(self, name):
        get(self, **self._packages[name], destination=self.build_folder, strip_root=True)

    def build(self):
        self._get_pypi_package("intel-opencl-rt")

    def package(self):
        if self.settings.os == "Windows":
            move_folder_contents(self, os.path.join(self.build_folder, "data", "Library"), self.package_folder)
            copy(self, "*", os.path.join(self.build_folder, "data"), self.package_folder)
        else:
            move_folder_contents(self, os.path.join(self.build_folder, "data"), self.package_folder)
        copy(self, "LICENSE.txt", self.build_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.package_folder, "share/doc/opencl/licensing"), os.path.join(self.package_folder, "licenses"))
        if self.settings.os != "Windows":
            rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "etc", "compiler"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "Scripts"))
        # Replace hard copies with symlinks
        if self.settings.os == "Linux":
            libdir = Path(self.package_folder, "lib")
            for p in list(libdir.glob("*.so.*.*")):
                target = str(p.parent / p.name.split(".", 1)[0])
                for suffix in p.suffixes[:-1]:
                    target += suffix
                    target_path = Path(target)
                    if target_path.exists():
                        target_path.unlink()
                        target_path.symlink_to(p.name)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_module_file_name", "OpenCL")
        self.cpp_info.set_property("cmake_file_name", "OpenCLICDLoader")
        self.cpp_info.set_property("cmake_target_name", "OpenCL::OpenCL")
        self.cpp_info.libs = ["OpenCL"]
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["etc"]
