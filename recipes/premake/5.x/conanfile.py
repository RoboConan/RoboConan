import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, VCVars

required_conan_version = ">=2.1"


class PremakeConan(ConanFile):
    name = "premake"
    description = (
        "Describe your software project just once, "
        "using Premake's simple and easy to read syntax, "
        "and build it everywhere"
    )
    license = "BSD-3-Clause"
    homepage = "https://premake.github.io"
    topics = ("build", "build-systems")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "lto": [True, False],
    }
    default_options = {
        "lto": False,
    }

    def config_options(self):
        if self.settings.os != "Windows" or is_msvc(self):
            self.options.rm_safe("lto")

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler
        if self.info.settings.build_type != "Debug":
            self.info.settings.build_type = "Release"

    def requirements(self):
        if self.settings.os == "Linux":
            self.requires("util-linux-libuuid/2.41")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=False)

    def generate(self):
        if is_msvc(self):
            vcvars = VCVars(self)
            vcvars.generate()

    def _patch_sources(self):
        if self.options.get_safe("lto", None) is False:
            replace_in_file(self, os.path.join(self.source_folder, "premake5.lua"),
                            '"LinkTimeOptimization"', "")

        # Add missing libuuid include dir
        if self.settings.os == "Linux":
            libuuid_info = self.dependencies["util-linux-libuuid"].cpp_info.aggregated_components()
            replace_in_file(self, os.path.join(self.source_folder, "Bootstrap.mak"),
                            " -luuid",
                            f" -luuid -I{libuuid_info.includedirs[0]} -L{libuuid_info.libdirs[0]}")

        # Fix mismatching win32 arch name
        replace_in_file(self, os.path.join(self.source_folder, "Bootstrap.mak"), "$(PLATFORM:x86=win32)", "$(VS_ARCH)")

    @property
    def _os_target(self):
        return {
            "FreeBSD": "bsd",
            "Windows": "windows",
            "Linux": "linux",
            "Macos": "macosx",
        }[str(self.settings.os)]

    @property
    def _arch(self):
        return {
            "x86": "x86",
            "x86_64": "x86_64",
            "armv7": "ARM",
            "armv8": "ARM64",
        }[str(self.settings.arch)]

    @property
    def _vs_ide_year(self):
        year = {
            "192": "2019",
            "191": "2017",
            "190": "2015",
            "180": "2013",
        }.get(str(self.settings.compiler.version), "2022")
        return year

    def build(self):
        self._patch_sources()
        make = "nmake" if is_msvc(self) else "make"
        config = "debug" if self.settings.build_type == "Debug" else "release"
        msdev = f"vs{self._vs_ide_year}" if is_msvc(self) else ""
        vs_arch = "x86" if self.settings.arch == "x86" else "x64"
        with chdir(self, self.source_folder):
            self.run(f"{make} -f Bootstrap.mak {self._os_target} PLATFORM={self._arch} CONFIG={config} MSDEV={msdev} VS_ARCH={vs_arch}")

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        suffix = ".exe" if self.settings.os == "Windows" else ""
        copy(self, f"*/premake5{suffix}",
             os.path.join(self.source_folder, "bin"),
             os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
