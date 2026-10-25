import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *

required_conan_version = ">=2.1"

class JomInstallerConan(ConanFile):
    name = "jom"
    description = "jom is a clone of nmake to support the execution of multiple independent commands in parallel"
    homepage = "http://wiki.qt.io/Jom"
    license = "GPL-3.0-only"
    topics = ("build", "make", "makefile", "nmake")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        pass

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def validate(self):
        if self.settings.os != "Windows" and (not self.settings_target or self.settings_target.os != "Windows"):
            raise ConanInvalidConfiguration(f"{self.ref} is only intended to be used on Windows or as a Windows build tool")

    def source(self):
        pass

    def build(self):
        get(self, **self.conan_data["sources"][self.version]["x86_64"])
        download(self, **self.conan_data["sources"][self.version]["license"], filename="LICENSE.GPL")

    def package(self):
        copy(self, "LICENSE.GPL", self.build_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.exe", self.build_folder, os.path.join(self.package_folder, "bin"))
        if os.name == "posix":
            jom = os.path.join(self.package_folder, "bin", "jom.exe")
            os.chmod(jom, os.stat(jom).st_mode | 0o111)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
