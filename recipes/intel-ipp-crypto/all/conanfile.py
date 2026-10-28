import os
from functools import cached_property
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout


class IntelIppCryptoConan(ConanFile):
    name = "intel-ipp-crypto"
    description = "Intel Cryptography Primitives Library"
    license = "Apache-2.0"
    homepage = "https://www.intel.com/content/www/us/en/developer/tools/oneapi/crypto-library.html"
    topics = ("intel", "oneapi", "cryptography", "pre-built")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "crypto_mb": [True, False],
    }
    default_options = {
        "shared": False,
        "crypto_mb": False,
    }
    options_description = {
        "crypto_mb": "Include the Crypto Multi-buffer Library",
    }

    @cached_property
    def _packages(self):
        with open(os.path.join(self.recipe_folder, "sources", f"{self.version}.yml")) as f:
            return yaml.safe_load(f)[str(self.settings.os)]

    def export(self):
        copy(self, f"{self.version}.yml", os.path.join(self.recipe_folder, "sources"),
             os.path.join(self.export_folder, "sources"))

    @property
    def _library_suffix(self):
        return "mt" if self.settings.os == "Windows" and not self.options.shared else ""

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.crypto_mb:
            self.requires("openssl/[^3]")
            if self.settings.os == "Linux" and self.options.shared:
                self.requires("intel-compiler-runtime/[^2026]")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(f"{self.settings.arch} is not supported")
        if self.options.shared and self.options.crypto_mb:
            if not self.dependencies["openssl"].options.shared:
                raise ConanInvalidConfiguration("The shared Crypto Multi-buffer Library requires openssl:shared=True")

    def _get_pypi_package(self, name):
        get(self, **self._packages[name], destination=self.build_folder, strip_root=True)

    def build(self):
        self._get_pypi_package("ipp-crypto-include")
        if self.options.shared:
            self._get_pypi_package("ipp-crypto")
            if self.settings.os == "Windows":
                self._get_pypi_package("ipp-crypto-devel")
        else:
            self._get_pypi_package("ipp-crypto-static")

    def package(self):
        if self.settings.os == "Windows":
            move_folder_contents(self, os.path.join(self.build_folder, "data", "Library"), self.package_folder)
            copy(self, "*", os.path.join(self.build_folder, "data", "include"),
                 os.path.join(self.package_folder, "include"))
        else:
            move_folder_contents(self, os.path.join(self.build_folder, "data"), self.package_folder)
        copy(self, "LICENSE.txt", self.build_folder, os.path.join(self.package_folder, "licenses"))

        # The wheel separates compatibility aggregators from the product
        # headers. Overlay them to reproduce the installed oneAPI layout.
        include_dir = os.path.join(self.package_folder, "include")
        ippcp_dir = os.path.join(include_dir, "ippcp")
        mkdir(self, ippcp_dir)
        for header in ["ippcp.h", "ippcpdefs.h", "ippcpversion.h", "ippversion.h"]:
            rename(self, os.path.join(include_dir, header), os.path.join(ippcp_dir, header))
        copy(self, "*", os.path.join(include_dir, "aggregator"), include_dir)
        rmdir(self, os.path.join(include_dir, "aggregator"))

        if not self.options.crypto_mb:
            rmdir(self, os.path.join(include_dir, "crypto_mb"))
            rm(self, "*crypto_mb*", os.path.join(self.package_folder, "lib"))
            rm(self, "*crypto_mb*", os.path.join(self.package_folder, "bin"))

        if self.settings.os == "Linux" and self.options.shared:
            libdir = Path(self.package_folder, "lib")
            for library in libdir.glob("*.so.*.*"):
                for suffix in [library.name.rsplit(".", 1)[0], library.name.split(".so", 1)[0] + ".so"]:
                    link = libdir / suffix
                    if link.exists():
                        link.unlink()
                    link.symlink_to(library.name)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "IPPCrypto")

        self.cpp_info.components["ippcp"].set_property("cmake_target_name", "IPPCrypto::ippcp")
        self.cpp_info.components["ippcp"].libs = [f"ippcp{self._library_suffix}"]
        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.components["ippcp"].defines = ["IPP_W32DLL"]

        if self.options.crypto_mb:
            self.cpp_info.components["crypto_mb"].set_property("cmake_target_name", "IPPCrypto::crypto_mb")
            self.cpp_info.components["crypto_mb"].libs = [f"crypto_mb{self._library_suffix}"]
            self.cpp_info.components["crypto_mb"].requires = ["openssl::crypto"]
            if self.settings.os == "Linux" and self.options.shared:
                self.cpp_info.components["crypto_mb"].requires.append(
                    "intel-compiler-runtime::intel-compiler-runtime"
                )

        self.runenv_info.define_path("IPPCRYPTOROOT", self.package_folder)
        self.buildenv_info.define_path("IPPCRYPTOROOT", self.package_folder)
