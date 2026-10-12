import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.4"


class LibexifConan(ConanFile):
    name = "libexif"
    homepage = "https://libexif.github.io/"
    license = "LGPL-2.1-or-later"
    description = "libexif is a library for parsing, editing, and saving EXIF data."
    topics = ("exif", "metadata", "parse", "edit")
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-nls" if self.options.i18n else "--disable-nls",
            "--disable-docs",
            "--disable-rpath",
        ])
        env = tc.environment()
        if is_msvc(self):
            compile_wrapper = unix_path(self, os.path.join(self.source_folder, "compile"))
            ar_wrapper = unix_path(self, os.path.join(self.source_folder, "ar-lib"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("LD", f"{compile_wrapper} link -nologo")
        tc.generate(env)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        if is_msvc(self) and self.options.shared:
            rename(self, os.path.join(self.package_folder, "lib", "exif.dll.lib"),
                         os.path.join(self.package_folder, "lib", "exif.lib"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libexif")
        self.cpp_info.libs = ["exif"]
        if self.options.i18n:
            self.cpp_info.resdirs = ["share"]
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["m"]
