import os
from functools import cached_property

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class IntelMPIConan(ConanFile):
    name = "intelmpi"
    description = "Intel MPI Library"
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://www.intel.com/content/www/us/en/developer/tools/oneapi/mpi-library.html"
    topics = ("intel", "oneapi", "mpi", "hpc", "pre-built")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    provides = ["mpi"]

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

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(f"{self.settings.arch} is not supported")

    def build(self):
        for package in ["impi-rt", "impi-devel"]:
            get(self, **self._packages[package], destination=self.build_folder, strip_root=True)

    def package(self):
        if self.settings.os == "Windows":
            move_folder_contents(self, os.path.join(self.build_folder, "data", "Library"), self.package_folder)
            license_dir = os.path.join(self.build_folder, "data", "share", "doc", "mpi", "licensing")
        else:
            move_folder_contents(self, os.path.join(self.build_folder, "data"), self.package_folder)
            license_dir = os.path.join(self.package_folder, "share", "doc", "mpi", "licensing")
        copy(self, "license.txt", license_dir, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "third-party-programs.txt", license_dir, os.path.join(self.package_folder, "licenses"), keep_path=False)
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "etc", "conda"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "MPI")
        self.cpp_info.set_property("pkg_config_name", "none")

        mpi_c = self.cpp_info.components["mpi-c"]
        mpi_c.set_property("cmake_target_name", "MPI::MPI_C")
        mpi_c.libs = ["impi" if self.settings.os == "Windows" else "mpi"]
        if self.settings.os == "Linux":
            mpi_c.system_libs = ["rt", "dl", "m", "pthread"]

        mpi_cxx = self.cpp_info.components["mpi-cxx"]
        mpi_cxx.set_property("cmake_target_name", "MPI::MPI_CXX")
        mpi_cxx.libs = ["impicxx" if self.settings.os == "Windows" else "mpicxx"]
        mpi_cxx.requires = ["mpi-c"]

        mpi_fortran = self.cpp_info.components["mpi-fortran"]
        mpi_fortran.set_property("cmake_target_name", "MPI::MPI_Fortran")
        mpi_fortran.includedirs.append(os.path.join("include", "mpi"))
        if self.settings.os == "Linux":
            mpi_fortran.libs = ["mpifort"]
        mpi_fortran.requires = ["mpi-c"]

        self.runenv_info.define_path("I_MPI_ROOT", self.package_folder)
