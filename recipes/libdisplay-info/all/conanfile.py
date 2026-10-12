import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class LibdisplayInfoConan(ConanFile):
    name = "libdisplay-info"
    description = "EDID and DisplayID library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/emersion/libdisplay-info"
    topics = ("display", "DisplayID", "EDID")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if not self.settings.os in ["FreeBSD", "Linux"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")

    def build_requirements(self):
        self.tool_requires("hwdata/0.376")
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "meson.build", "subdir('test')", "# subdir('test')")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.build_context_activated.append("hwdata")
        deps.generate()

        if cross_building(self):
            # required for dependency(..., native: true) in meson.build
            env = Environment()
            env.define_path("PKG_CONFIG_FOR_BUILD", self.conf.get("tools.gnu:pkg_config", default="pkgconf", check_type=str))
            env.define_path("PKG_CONFIG_PATH_FOR_BUILD", self.generators_folder)
            env.vars(self).save_script("pkg_config_for_build_env")


    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["display-info"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
