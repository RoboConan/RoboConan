import os
from functools import cached_property

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class IntelTcmlibConan(ConanFile):
    name = "intel-tcmlib"
    description = ("Thread Composability Manager coordinates CPU resources usage between Intel oneAPI Threading Building Blocks (TBB)"
                   " and Intel OpenMP to avoid excessive oversubscription when both runtimes are used within a process.")
    # https://intel.ly/393CijO
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://pypi.org/project/tcmlib/"
    topics = ("intel", "tbb", "pre-built")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    default_options = {
        "hwloc/*:shared": True,
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
        # Can't unvendor hwloc on Windows because the libhwloc-15.dll name does not match hwloc.dll from the recipe
        if self.settings.os == "Linux":
            self.requires("hwloc/[^2.12]")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(f"{self.settings.arch} is not supported")
        if self.settings.os == "Linux" and not self.dependencies["hwloc"].options.shared:
            raise ConanInvalidConfiguration("intel-tcmlib requires hwloc:shared=True")

    def _get_pypi_package(self, name):
        get(self, **self._packages[name], destination=self.build_folder, strip_root=True)

    def build(self):
        self._get_pypi_package("tcmlib")

    def package(self):
        if self.settings.os == "Windows":
            move_folder_contents(self, os.path.join(self.build_folder, "data", "Library"), self.package_folder)
            copy(self, "*", os.path.join(self.build_folder, "data"), self.package_folder)
        else:
            move_folder_contents(self, os.path.join(self.build_folder, "data"), self.package_folder)
        copy(self, "*", os.path.join(self.package_folder, "share/doc/tcm/licensing"), os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        if self.settings.os == "Linux":
            rm(self, "libhwloc.*", os.path.join(self.package_folder, "lib"))
            for lib in ["tcm", "tcm_debug"]:
                libfile = f"lib{lib}.so.{self.version}"
                major = Version(self.version).major
                for target in [
                    f"lib{lib}.so.{major}",
                    f"lib{lib}.so",
                ]:
                    os.unlink(os.path.join(self.package_folder, "lib", target))
                    os.symlink(libfile, os.path.join(self.package_folder, "lib", target))

    def package_info(self):
        self.cpp_info.includedirs = []
        if self.settings.os == "Windows":
            self.cpp_info.libdirs = []
        else:
            self.cpp_info.bindirs = []
