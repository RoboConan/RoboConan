import os.path

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import PkgConfig
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "AutotoolsToolchain", "PkgConfigDeps"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualBuildEnv(self).generate(scope="run")

    def test(self):
        xkb_base = PkgConfig(self, "xkeyboard-config").variables["xkb_base"]
        self.output.info(f"xkb_base path: {xkb_base}")
        assert os.path.isdir(xkb_base)
