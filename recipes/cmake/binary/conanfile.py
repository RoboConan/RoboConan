import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class CMakeConan(ConanFile):
    name = "cmake"
    package_type = "application"
    description = "CMake, the cross-platform, open-source build system."
    topics = ("build", "installer")
    homepage = "https://github.com/Kitware/CMake"
    license = "BSD-3-Clause"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.arch not in ["x86_64", "armv8", "armv8|x86_64"]:
            raise ConanInvalidConfiguration("CMake binaries are only provided for x86_64 and armv8 architectures. " +
                        "Consider using the system cmake with [platform_tool_requires] section in your profile.")

        if self.settings.os == "Windows" and self.settings.arch == "armv8" and Version(self.version) < "3.24":
            raise ConanInvalidConfiguration("CMake only supports ARM64 binaries on Windows starting from 3.24")

    def build(self):
        arch = str(self.settings.arch) if self.settings.os != "Macos" else "universal"
        get(self, **self.conan_data["sources"][self.version][str(self.settings.os)][arch], strip_root=True)

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type
        self.info.settings.arch = "armv8|x86_64"

    def package(self):
        copy(self, "*", src=self.build_folder, dst=self.package_folder)

        if self.settings.os == "Macos":
            docs_folder = os.path.join(self.build_folder, "CMake.app", "Contents", "doc", "cmake")
        else:
            docs_folder = os.path.join(self.build_folder, "doc", "cmake")

        licensefile = "LICENSE.rst" if Version(self.version) >= "4.0.0" else "Copyright.txt"
        copy(self, licensefile, src=docs_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        if self.settings.os != "Macos":
            # Remove unneeded folders (also cause long paths on Windows)
            # Note: on macOS we don't want to modify the bundle contents
            #       to preserve signature validation
            rmdir(self, os.path.join(self.package_folder, "doc"))
            rmdir(self, os.path.join(self.package_folder, "man"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        if self.settings.os == "Macos":
            bindir = os.path.join(self.package_folder, "CMake.app", "Contents", "bin")
            self.cpp_info.bindirs = [bindir]
