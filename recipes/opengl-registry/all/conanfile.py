import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class OpenGLRegistryConan(ConanFile):
    name = "opengl-registry"
    description = "OpenGL, OpenGL ES, and OpenGL ES-SC API and Extension Registry."
    license = "Apache-2.0"
    topics = ("opengl-registry", "opengl")
    homepage = "https://github.com/KhronosGroup/OpenGL-Registry"
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
        license_data = load(self, os.path.join(self.source_folder, "api", "GL", "glext.h"))
        begin = license_data.find("/*") + len("/*")
        end = license_data.find("*/")
        license_data = license_data[begin:end]
        license_data = license_data.replace("**", "")
        return license_data

    def package(self):
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), self._extract_license())
        copy(self, "*", src=os.path.join(self.source_folder, "api"), dst=os.path.join(self.package_folder, "include"))
        copy(self, "*", src=os.path.join(self.source_folder, "xml"), dst=os.path.join(self.package_folder, "share", "opengl-registry", "xml"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
