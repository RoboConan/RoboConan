import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class XFontsEncodingsConan(ConanFile):
    name = "xfonts-encodings"
    description = "Font encoding tables for libfontenc"
    license = "DocumentRef-COPYING:LicenseRef-xfonts-encodings-public-domain"
    homepage = "https://gitlab.freedesktop.org/xorg/font/encodings"
    topics = ("xorg", "x11")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        self.tool_requires("mkfontscale/[*]")
        # Also requires gzip, assumed to be available on the system

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Don't rely on system fontutil to set datadir path
        replace_in_file(self, "meson.build", "fontutil.found()", "false")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]

        encodings_dir = os.path.join(self.package_folder, "share", "fonts", "X11", "encodings")
        self.runenv_info.define_path("FONT_ENCODINGS_DIRECTORY", encodings_dir)
