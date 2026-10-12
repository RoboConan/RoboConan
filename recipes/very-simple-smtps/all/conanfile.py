import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class VerySimpleSmtpsConan(ConanFile):
    name = "very-simple-smtps"
    description = "Library that allows applications to send emails with binary attachments"
    license = "MIT"
    homepage = "https://github.com/matthewT53/Very-Simple-SMTPS/releases"
    topics = ("email", "smtps", "attachments")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": False,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("doctest/2.4.11")
        self.requires("libcurl/[>=7.78.0 <9]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("very-simple-smtps is only supported by Linux")

        if self.settings.compiler == "clang" and self.settings.compiler.libcxx == "libc++":
            raise ConanInvalidConfiguration("very-simple-smtps cannot use libc++")

        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.generate()
        tc = PkgConfigDeps(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "include/*.hpp", self.source_folder, self.package_folder)
        meson = Meson(self)
        meson.install()

        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))

        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.libs = ["smtp_lib"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
