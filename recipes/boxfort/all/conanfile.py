import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class BoxfortConan(ConanFile):
    name = "boxfort"
    description = "Convenient & cross-platform sandboxing C library"
    license = "MIT"
    homepage = "https://github.com/Snaipe/BoxFort"
    topics = ("sandboxing",)
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "arena_reopen_shm": [True, False],
        "arena_file_backed": [True, False],
    }
    default_options = {
        "arena_reopen_shm": False,
        "arena_file_backed": False,
    }
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["samples"] = False
        tc.project_options["tests"] = False
        tc.project_options["arena_reopen_shm"] = self.options.arena_reopen_shm
        tc.project_options["arena_file_backed"] = self.options.arena_file_backed
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "boxfort")
        self.cpp_info.libs = ["boxfort"]
        if not self.options.get_safe("shared"):
            self.cpp_info.defines.append("BXF_STATIC_LIB=1")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["pthread", "rt", "m"])
            self.cpp_info.cflags.append("-pthread")

