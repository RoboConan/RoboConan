import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class LibsecretConan(ConanFile):
    name = "libsecret"
    description = "A library for storing and retrieving passwords and other secrets"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Projects/Libsecret"
    topics = ("gobject", "password", "secret")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "crypto": [False, "libgcrypt", "gnutls"],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "crypto": "libgcrypt",
        "with_introspection": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def config_options(self):
        if self.settings.os != "Linux":
            # libgcrypt recipe is currently only available on Linux
            self.options.crypto = False

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        if self.options.get_safe("crypto") == "libgcrypt":
            self.requires("libgcrypt/[^1.10.3]")
        elif self.options.get_safe("crypto") == "gnutls":
            self.requires("gnutls/[^3.8.2]")
        if self.options.with_introspection:
            self.requires("glib-gir/[^2.82]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} recipe is not yet compatible with Windows.")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("glib/<host_version>")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["introspection"] = "true" if self.options.with_introspection else "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["manpage"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["bash_completion"] = "disabled"
        tc.project_options["crypto"] = str(self.options.crypto) if self.options.crypto else "disabled"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        if not self.options.i18n:
            save(self, os.path.join(self.source_folder, "po", "meson.build"), "")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libsecret-1")
        self.cpp_info.includedirs = [os.path.join("include", "libsecret-1")]
        self.cpp_info.libs = ["secret-1"]
        if self.options.i18n:
            self.cpp_info.resdirs = ["share"]
        self.cpp_info.requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0"]
        if self.options.get_safe("crypto") == "libgcrypt":
            self.cpp_info.requires.append("libgcrypt::libgcrypt")
        elif self.options.get_safe("crypto") == "gnutls":
            self.cpp_info.requires.append("gnutls::gnutls")
        if self.options.with_introspection:
            self.cpp_info.requires.append("glib-gir::glib-gir")
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
