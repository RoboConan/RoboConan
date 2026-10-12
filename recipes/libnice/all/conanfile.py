import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc_static_runtime

required_conan_version = ">=2.4"


class LibniceConan(ConanFile):
    name = "libnice"
    description = "a GLib ICE implementation"
    license = "LGPL-2.1-or-later OR MPL-1.1"
    homepage = "https://libnice.freedesktop.org/"
    topics = ("ice", "stun", "turn")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "crypto_library": ["openssl", "win32"],
        "with_gstreamer": [True, False],
        "with_gtk_doc": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_gstreamer": False,
        "with_gtk_doc": False,
        "with_introspection": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            self.options.crypto_library = "win32"
        else:
            self.options.crypto_library = "openssl"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        if self.options.crypto_library == "openssl":
            self.requires("openssl/[>=1.1 <4]")
        if self.options.with_gstreamer:
            self.requires("gstreamer/[^1.24]")
        if self.options.with_introspection:
            self.requires("glib-gir/[^2.82]")

    def validate(self):
        if self.settings.os != "Windows" and self.options.crypto_library == "win32":
            raise ConanInvalidConfiguration(
                f"-o {self.ref}:crypto_library=win32 is not supported on non-Windows")
        if self.settings.os == "Windows" and self.options.with_gtk_doc:
            raise ConanInvalidConfiguration(
                f"-o {self.ref}:with_gtk_doc=True is not support on Windows")
        if is_msvc_static_runtime(self) and self.dependencies["glib"].options.shared:
            raise ConanInvalidConfiguration(
                "-o glib/*:shared=True with static runtime is not supported")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        self.tool_requires("pkgconf/[<4]")
        self.tool_requires("glib/<host_version>")  # for glib-mkenums
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["gupnp"] = "disabled"
        tc.project_options["gstreamer"] = "enabled" if self.options.with_gstreamer else "disabled"
        tc.project_options["crypto-library"] = "auto" if self.options.crypto_library == "win32" else str(self.options.crypto_library)
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["gtk_doc"] = "disabled" if self.options.with_gtk_doc else "disabled"
        tc.project_options["introspection"] = "enabled" if self.options.with_introspection else "disabled"
        tc.generate()

        tc = PkgConfigDeps(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "gstreamer-1.0", "pkgconfig"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        if self.settings.os == "Windows":
            if not self.options.shared:
                with chdir(self, os.path.join(self.package_folder, "lib")):
                    rename(self, "libnice.a", "nice.lib")
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.components["libnice_"].set_property("pkg_config_name", "nice")
        self.cpp_info.components["libnice_"].set_property("pkg_config_custom_content", "upnp_enabled=false")
        self.cpp_info.components["libnice_"].libs = ["nice"]
        self.cpp_info.components["libnice_"].includedirs.append("include/nice")
        self.cpp_info.components["libnice_"].requires = ["glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0", "glib::gthread-2.0"]
        if self.options.crypto_library == "openssl":
            self.cpp_info.components["libnice_"].requires.append("openssl::openssl")
        if self.settings.os == "Windows":
            self.cpp_info.components["libnice_"].system_libs.append("advapi32")

        if self.options.with_gstreamer:
            self.cpp_info.components["gstnice"].set_property("pkg_config_name", "gstnice")
            self.cpp_info.components["gstnice"].libs = ["gstnice"]
            self.cpp_info.components["gstnice"].libdirs = ["lib/gstreamer-1.0"]
            self.cpp_info.components["gstnice"].requires = ["libnice_", "gstreamer::gstreamer-base-1.0"]

        if self.options.with_introspection:
            self.cpp_info.components["libnice_"].resdirs = ["share"]
            self.cpp_info.components["libnice_"].requires.append("glib-gir::glib-gir")
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
