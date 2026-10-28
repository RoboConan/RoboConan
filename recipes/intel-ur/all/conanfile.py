import os
from functools import cached_property
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class IntelUrConan(ConanFile):
    name = "intel-ur"
    description = "Intel oneAPI Unified Runtime Libraries package"
    # https://intel.ly/393CijO
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://pypi.org/project/intel-cmplr-lib-ur/"
    topics = ("intel", "oneapi", "pre-built")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    default_options = {
        "umf/*:shared": True,
        "zlib-ng/*:shared": True,
    }

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
        self.requires("umf/[^1]")
        if self.settings.os == "Linux":
            self.requires("zlib-ng/[^2.0]")
        version = ".".join(str(self.version).split(".")[:2])
        self.requires(f"intel-compiler-runtime/[~{version}]")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(f"{self.settings.arch} is not supported")
        if not self.dependencies["umf"].options.shared:
            raise ConanInvalidConfiguration("intel-ur requires umf:shared=True")
        if self.settings.os == "Linux" and not self.dependencies["zlib-ng"].options.shared:
            raise ConanInvalidConfiguration("intel-ur requires zlib-ng:shared=True")

    def _get_pypi_package(self, name):
        get(self, **self._packages[name], destination=self.build_folder, strip_root=True)

    def build(self):
        self._get_pypi_package("intel-cmplr-lib-ur")
        if self.settings.os == "Windows":
            move_folder_contents(self, os.path.join(self.build_folder, "data", "Library"), self.source_folder)
        else:
            move_folder_contents(self, os.path.join(self.build_folder, "data"), self.source_folder)

    def package(self):
        move_folder_contents(self, self.source_folder, self.package_folder)
        copy(self, "LICENSE.txt", self.build_folder, os.path.join(self.package_folder, "licenses"))
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
        self.cpp_info.includedirs = []
        if self.settings.os == "Windows":
            self.cpp_info.libdirs = []
        else:
            self.cpp_info.libs = ["ur_loader"]
