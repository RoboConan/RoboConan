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


class IntelCompilerRuntimeConan(ConanFile):
    name = "intel-compiler-runtime"
    description = "Intel oneAPI compiler runtime libraries"
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://pypi.org/project/intel-cmplr-lib-rt/"
    topics = ("intel", "oneapi", "runtime", "pre-built")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    default_options = {
        "umf/*:shared": True,
        "zlib/*:shared": True,
    }

    @cached_property
    def _packages(self):
        with open(os.path.join(self.recipe_folder, "sources", f"{self.version}.yml")) as f:
            return yaml.safe_load(f)[str(self.settings.os)]

    def export(self):
        copy(self, f"{self.version}.yml", os.path.join(self.recipe_folder, "sources"),
             os.path.join(self.export_folder, "sources"))

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.settings.os == "Windows":
            if Version(self.version) >= "2025.3":
                self.requires("umf/[^1]")
        else:
            self.requires("zlib/[^1.2]")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(f"{self.settings.arch} is not supported")
        if self.settings.os == "Windows" and Version(self.version) >= "2025.3":
            if not self.dependencies["umf"].options.shared:
                raise ConanInvalidConfiguration("intel-compiler-runtime requires umf:shared=True")
        if self.settings.os == "Linux" and not self.dependencies["zlib"].options.shared:
            raise ConanInvalidConfiguration("intel-compiler-runtime requires zlib:shared=True")

    def build(self):
        get(self, **self._packages["intel-cmplr-lib-rt"], destination=self.build_folder, strip_root=True)

    def package(self):
        if self.settings.os == "Windows":
            move_folder_contents(self, os.path.join(self.build_folder, "data", "Library"), self.package_folder)
        else:
            move_folder_contents(self, os.path.join(self.build_folder, "data"), self.package_folder)
        copy(self, "LICENSE.txt", self.build_folder, os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "Linux":
            libdir = Path(self.package_folder, "lib")
            for p in list(libdir.glob("*.so.*.*")) + list(libdir.glob("libintlc.so.*")):
                target = str(p.parent / p.name.split(".", 1)[0])
                for suffix in p.suffixes[:-1]:
                    target += suffix
                    target_path = Path(target)
                    if target_path.exists():
                        target_path.unlink()
                        target_path.symlink_to(p.name)

    def package_info(self):
        self.cpp_info.includedirs = []
