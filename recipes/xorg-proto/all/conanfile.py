import os
import re
from pathlib import Path

import yaml
from conan import ConanFile
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class XorgProtoConan(ConanFile):
    name = "xorg-proto"
    package_type = "header-library"
    description = "This package provides the headers and specification documents defining " \
        "the core protocol and (many) extensions for the X Window System."
    topics = ("specification", "x-window")
    license = "X11"
    homepage = "https://gitlab.freedesktop.org/xorg/proto/xorgproto"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("automake/[^1.18.1]")
        self.tool_requires("xorg-macros/[^1.20.2]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def package_id(self):
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        if is_msvc(self):
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
        tc.generate(env)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    @property
    def _pc_data_yml_path(self):
        return Path(self.package_folder, "share", "conan", self.name, "pc_data.yml")

    def _read_pc_data(self):
        pc_data = {}
        for path in Path(self.package_folder, "share", "pkgconfig").glob("*.pc"):
            pc_text = path.read_text(encoding="utf-8")
            name = re.search("^Name: ([^\n$]+)[$\n]", pc_text, flags=re.MULTILINE).group(1)
            version = re.search("^Version: ([^\n$]+)[$\n]", pc_text, flags=re.MULTILINE).group(1)
            pc_data[path.stem] = {
                "version": version,
                "name": name,
            }
        return pc_data

    def package(self):
        copy(self, "COPYING-*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        save(self, self._pc_data_yml_path, yaml.dump(self._read_pc_data()))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "pkgconfig"))

    def package_info(self):
        for filename, name_version in yaml.safe_load(self._pc_data_yml_path.read_text()).items():
            self.cpp_info.components[filename].set_property("pkg_config_name", filename)
            self.cpp_info.components[filename].set_property("component_version", name_version["version"])
            self.cpp_info.components[filename].libdirs = []

        self.cpp_info.components["xproto"].includedirs.append(os.path.join("include", "X11"))
