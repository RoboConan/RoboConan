import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class LibGphoto2(ConanFile):
    name = "libgphoto2"
    description = "The libgphoto2 camera access and control library."
    homepage = "http://www.gphoto.org/"
    license = "LGPL-2.1"
    topics = ("gphoto2", "libgphoto2", "libgphoto", "photo")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "i18n": [True, False],
        "with_libusb": [True, False],
        "with_libcurl": [True, False],
        "with_libxml2": [True, False],
        "with_libexif": [True, False],
        "with_libjpeg": [True, False],
    }
    default_options = {
        "i18n": False,
        "with_libusb": True,
        "with_libcurl": True,
        "with_libxml2": True,
        "with_libexif": True,
        "with_libjpeg": True,
    }
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libtool/[^2.4.7]")
        if self.options.with_libusb:
            self.requires("libusb/[^1.0.26]")
        if self.options.with_libcurl:
            self.requires("libcurl/[>=7.78.0 <9]")
        if self.options.with_libxml2:
            self.requires("libxml2/[^2.12.5]")
        if self.options.with_libexif:
            self.requires("libexif/[>=0.6.24 <0.7]")
        if self.options.with_libjpeg:
            self.requires("libjpeg-meta/latest")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("Visual Studio not supported yet")

    def build_requirements(self):
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        tc = AutotoolsToolchain(self)
        auto_no = lambda v: "auto" if v else "no"
        tc.configure_args.extend([
            f"--with-libcurl={auto_no(self.options.with_libcurl)}",
            f"--with-libexif={auto_no(self.options.with_libexif)}",
            f"--with-libxml-2.0={auto_no(self.options.with_libxml2)}",
            "--enable-nls" if self.options.i18n else "--disable-nls",
            "utilsdir=${prefix}/bin",
        ])
        if not self.options.with_libjpeg:
            tc.configure_args.append("--without-jpeg")
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()
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
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libgphoto2")
        self.cpp_info.libs = ["gphoto2", "gphoto2_port"]
        self.cpp_info.includedirs.append(os.path.join("include", "gphoto2"))
        self.cpp_info.resdirs = ["share"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["dl"]
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["m"]
