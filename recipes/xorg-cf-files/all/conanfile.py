import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, PkgConfigDeps, GnuToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class XorgCfFilesConan(ConanFile):
    name = "xorg-cf-files"
    # package_type = "build-scripts" # see https://github.com/conan-io/conan/issues/13431
    description = "Imake configuration files & templates"
    topics = ("imake", "xorg", "template", "configuration", "obsolete")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/util/cf"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("xorg-proto/[>=2024.1]")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.arch
        del self.info.settings.build_type
        # self.info.settings.os  # FIXME: can be removed once c3i is able to test multiple os'es from one common package

    def validate(self):
        if is_apple_os(self):
            raise ConanInvalidConfiguration(f"{self.ref} does not support Apple operating systems.")
        if self.settings.compiler == "clang":
            # See https://github.com/conan-io/conan-center-index/pull/16267#issuecomment-1469824504
            raise ConanInvalidConfiguration("Recipe cannot be built with clang")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        self.tool_requires("xorg-macros/[^1.20.2]")
        if is_msvc(self):
            self.tool_requires("automake/[^1.18.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        tc = GnuToolchain(self)
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        x11_config_files = os.path.join(self.package_folder, "lib", "X11", "config")
        self.conf_info.define("user.xorg-cf-files:config-path", x11_config_files)
