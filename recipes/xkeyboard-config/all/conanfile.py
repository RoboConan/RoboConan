import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class XkeyboardConfigConan(ConanFile):
    name = "xkeyboard-config"
    description = "Keyboard configuration database for X11"
    license = "HPND AND HPND-sell-variant AND X11 AND X11-distribute-modifications-variant AND MIT AND MIT-open-group AND xkeyboard-config-Zinoviev"
    homepage = "https://gitlab.freedesktop.org/xkeyboard-config/xkeyboard-config"
    topics = ("xorg", "x11", "keyboard")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "i18n": [True, False],
    }
    default_options = {
        "i18n": False,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD", "Android"]:
            raise ConanInvalidConfiguration("This recipe supports only Linux and FreeBSD")

    def package_id(self):
        self.info.clear()

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def _patch_sources(self):
        replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                        "enable_pytest = ", "enable_pytest = false #")
        if not self.options.i18n:
            save(self, os.path.join(self.source_folder, "po", "meson.build"), "")

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "share", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        if Version(self.version) >= "2.45":
            # Fix an absolute-path symlink to the new location
            os.unlink(os.path.join(self.package_folder, "share", "X11", "xkb"))
            os.symlink("../xkeyboard-config-2", os.path.join(self.package_folder, "share", "X11", "xkb"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "xkeyboard-config")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]

        self.cpp_info.set_property("pkg_config_custom_content", "\n".join([
            "datadir=${prefix}/share",
            "xkb_base=${datadir}/X11/xkb"
        ]))
