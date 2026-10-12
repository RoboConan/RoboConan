import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class LibfuseConan(ConanFile):
    name = "libfuse"
    homepage = "https://github.com/libfuse/libfuse"
    license = "LGPL-2.1"
    description = "The reference implementation of the Linux FUSE interface"
    topics = ("fuse", "filesystem", "linux")
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
        if self.settings.os not in ("Linux", "FreeBSD"):
            raise ConanInvalidConfiguration("libfuse supports only Linux and FreeBSD")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["examples"] = False
        tc.project_options["utils"] = False
        tc.project_options["tests"] = False
        tc.project_options["useroot"] = False
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "fuse3")
        self.cpp_info.libs = ["fuse3"]
        self.cpp_info.includedirs = [os.path.join("include", "fuse3")]
        self.cpp_info.system_libs = ["pthread"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["dl", "rt"])
