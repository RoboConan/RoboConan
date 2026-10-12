import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("wayland/[^1.22.0]")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("wayland/<host_version>")

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.build_context_activated.append("wayland")
        deps.build_context_folder = os.path.join(self.generators_folder, "build")
        deps.generate()

        if cross_building(self):
            # required for dependency(..., native: true) in meson.build
            env = Environment()
            env.define_path("PKG_CONFIG_FOR_BUILD", self.conf.get("tools.gnu:pkg_config", default="pkgconf", check_type=str))
            env.define_path("PKG_CONFIG_PATH_FOR_BUILD", os.path.join(self.generators_folder, "build"))
            env.vars(self).save_script("pkg_config_for_build_env")

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(cmd, env="conanrun")
