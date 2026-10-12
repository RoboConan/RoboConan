import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class LibSoupConan(ConanFile):
    name = "libsoup"
    description = "HTTP client/server library for GNOME"
    license = "LGPL-2.0-only"
    homepage = "https://gitlab.gnome.org/GNOME/libsoup"
    topics = ("http", "gnome", "gobject")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "gssapi": [True, False],
        "with_brotli": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "gssapi": False,
        "with_brotli": True,
        "with_introspection": False,
    }
    languages = ["C"]
    implements = ["auto_shared_fpic"]

    python_requires = "conan-utils/latest"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        self.requires("libnghttp2/[^1.61.0]")
        self.requires("sqlite3/[>=3.45.0 <4]")
        self.requires("libpsl/[>=0.21.5 <1]")
        self.requires("zlib-ng/[^2.0]")
        if self.options.with_brotli:
            self.requires("brotli/[^1.1.0]")
        if self.options.gssapi:
            self.requires("krb5/[^1.21.2]")
        if self.options.with_introspection:
            self.requires("glib-gir/[^2.82]")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("glib/<host_version>")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        def feature(v): return "enabled" if v else "disabled"
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["tests"] = "false"
        tc.project_options["pkcs11_tests"] = "disabled"
        tc.project_options["autobahn"] = "disabled"
        tc.project_options["tls_check"] = "false"
        tc.project_options["docs"] = "disabled"
        tc.project_options["vapi"] = "disabled"
        tc.project_options["ntlm"] = "disabled"  # TODO
        tc.project_options["gssapi"] = feature(self.options.gssapi)
        tc.project_options["introspection"] = feature(self.options.with_introspection)
        tc.project_options["brotli"] = feature(self.options.with_brotli)
        tc.project_options["sysprof"] = "disabled"
        tc.generate()

        deps = PkgConfigDeps(self)
        if self.options.gssapi:
            deps.set_property("krb5", "pkg_config_name", "krb5-gssapi")
        deps.generate()

    def build(self):
        if not self.options.gssapi:
            # the disabled gssapi dep is not handled correctly in libsoup/meson.build
            replace_in_file(self, os.path.join(self.source_folder, "libsoup", "meson.build"),
                            "gssapi_dep,", "")
        if not self.options.i18n:
            save(self, os.path.join(self.source_folder, "po", "meson.build"), "")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        name = "libsoup-3.0"
        self.cpp_info.components[name].set_property("pkg_config_name", name)
        self.cpp_info.components[name].libs = ["soup-3.0"]
        self.cpp_info.components[name].includedirs.append(os.path.join("include", name))
        self.cpp_info.components[name].resdirs = ["share"]
        self.cpp_info.components[name].requires = [
            "glib::glib-2.0",
            "glib::gmodule-no-export-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "sqlite3::sqlite3",
            "libpsl::libpsl",
            "zlib-ng::zlib-ng",
            "libnghttp2::libnghttp2",
        ]
        if self.options.with_brotli:
            self.cpp_info.components[name].requires.append("brotli::brotlidec")
        if self.options.gssapi:
            self.cpp_info.components[name].requires.append("krb5::krb5-gssapi")
        if self.options.with_introspection:
            self.cpp_info.components[name].requires.append("glib-gir::glib-gir")
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
