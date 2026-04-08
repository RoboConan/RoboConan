import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class EglHeadersConan(ConanFile):
    name = "egl-headers"
    description = "EGL Header files."
    license = "Apache-2.0"
    topics = ("egl-headers", "egl")
    homepage = "https://github.com/KhronosGroup/EGL-Registry"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("khrplatform/0.0+git.20200529")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _extract_license(self):
        license_data = load(self, os.path.join(self.source_folder, "api", "EGL", "egl.h"))
        begin = license_data.find("/*") + len("/*")
        end = license_data.find("*/")
        license_data = license_data[begin:end]
        license_data = license_data.replace("**", "")
        return license_data

    def package(self):
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), self._extract_license())
        copy(self, "*", src=os.path.join(self.source_folder, "api", "EGL"), dst=os.path.join(self.package_folder, "include", "EGL"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
