import os
import re
from functools import cached_property
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.21"  # for cmake_extra_variables


class IntelIppConan(ConanFile):
    name = "intel-ipp"
    description = "Intel Integrated Performance Primitives"
    license = "LicenseRef-Intel-Simplified-Software-License"
    homepage = "https://www.intel.com/content/www/us/en/developer/tools/oneapi/ipp.html"
    topics = ("intel", "oneapi", "image-processing", "signal-processing", "pre-built")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "threading": ["openmp", "tbb"],
    }
    default_options = {
        "shared": False,
        # Avoid mixing Intel OpenMP with the openmp/system runtime used by
        # most RoboConan packages.
        "threading": "tbb",
    }
    options_description = {
        "threading": "Threading Layer variant used by the IPP threading components",
    }

    @cached_property
    def _packages(self):
        return self.conan_data["sources"][self.version][str(self.settings.os)]

    @property
    def _library_suffix(self):
        return "mt" if self.settings.os == "Windows" and not self.options.shared else ""

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.threading == "openmp":
            self.requires("intel-openmp/[>=2025]")
        else:
            self.requires("onetbb/[>=2021]")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(f"{self.settings.arch} is not supported")

    def _get_pypi_package(self, name):
        get(self, **self._packages[name], destination=self.build_folder, strip_root=True)

    def build(self):
        self._get_pypi_package("ipp-devel")
        self._get_pypi_package("ipp-include")
        self._get_pypi_package("ipp-static")
        if self.options.shared:
            self._get_pypi_package("ipp")

    def package(self):
        if self.settings.os == "Windows":
            move_folder_contents(self, os.path.join(self.build_folder, "data", "Library"), self.package_folder)
        else:
            move_folder_contents(self, os.path.join(self.build_folder, "data"), self.package_folder)
        copy(self, "LICENSE.txt", self.build_folder, os.path.join(self.package_folder, "licenses"))

        libdir = os.path.join(self.package_folder, "lib")
        other_threading = "tbb" if self.options.threading == "openmp" else "omp"
        rm(self, f"*_tl_{other_threading}*", libdir)

        if self.options.shared:
            if self.settings.os == "Windows":
                rm(self, "*mt*.lib", libdir)
                rm(self, f"*_tl_{other_threading}*", os.path.join(self.package_folder, "bin"))
            else:
                rm(self, "*.a", libdir, excludes=["libipp_iw.a"])
                for library in Path(libdir).glob("*.so.*"):
                    link = Path(str(library).rsplit(".so", 1)[0] + ".so")
                    if not link.exists():
                        link.symlink_to(library.name)
        else:
            if self.settings.os == "Windows":
                components = ["ippcc", "ippcore", "ippcv", "ippdc", "ippe", "ippi", "ipps", "ippvm"]
                for component in components:
                    rm(self, f"{component}.lib", libdir)
                for component in ["ippcc", "ippcore", "ippcv", "ippi"]:
                    rm(self, f"{component}_tl_*.lib", libdir)
                rmdir(self, os.path.join(self.package_folder, "bin"))
            else:
                rm(self, "*.so*", libdir)

    @property
    def _interface_version(self):
        version_header = load(self, os.path.join(self.package_folder, "include", "ipp", "ippversion.h"))
        major = re.search(r"#define IPP_INTERFACE_VERSION_MAJOR\s+(\d+)", version_header).group(1)
        minor = re.search(r"#define IPP_INTERFACE_VERSION_MINOR\s+(\d+)", version_header).group(1)
        return f"{major}.{minor}"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "IPP")
        # IPPConfigVersion.cmake uses the library interface version from ippversion.h,
        # not the product/distribution version.
        self.cpp_info.set_property("system_package_version", self._interface_version)
        self.cpp_info.set_property("cmake_config_version_compat", "SameMajorVersion")
        self.cpp_info.set_property("cmake_extra_variables", {
            "IPP_SHARED": bool(self.options.shared),
            "IPP_TL_VARIANT": "OpenMP" if self.options.threading == "openmp" else "TBB",
        })

        dependencies = {
            "ipp_iw": [],
            "ippe": [],
            "ippcore": [],
            "ippvm": ["ippcore"],
            "ipps": ["ippvm"],
            "ippdc": ["ipps"],
            "ippi": ["ipps"],
            "ippcc": ["ippi"],
            "ippcv": ["ippi"],
            "ippcore_tl": [],
            "ippi_tl": ["ippi", "ippcore_tl"],
            "ippcc_tl": ["ippcc", "ippi_tl"],
            "ippcv_tl": ["ippcv", "ippi_tl"],
        }

        if self.options.threading == "openmp":
            dependencies["ippcore_tl"].append("intel-openmp::intel-openmp")
        else:
            dependencies["ippcore_tl"].append("onetbb::libtbb")

        for name, requires in dependencies.items():
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", f"IPP::{name}")
            component.requires = requires
            if name.endswith("_tl"):
                threading_suffix = "omp" if self.options.threading == "openmp" else "tbb"
                component.libs = [f"{name.removesuffix('_tl')}{self._library_suffix}_tl_{threading_suffix}"]
            elif name == "ipp_iw":
                component.libs = [name]
            else:
                component.libs = [f"{name}{self._library_suffix}"]

        self.cpp_info.components["ipp_iw"].includedirs.extend([
            "include/ipp",
            "include/ipp/iw",
            "include/ipp/iw++",
        ])

        self.runenv_info.define_path("IPPROOT", self.package_folder)
        self.buildenv_info.define_path("IPPROOT", self.package_folder)
