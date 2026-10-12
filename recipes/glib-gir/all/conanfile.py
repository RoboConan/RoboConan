import os
from pathlib import Path

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


# This package duplicates glib somewhat, but is necessary to break the
# gobject-introspection <-> glib circular dependency.


class GLibGIRConan(ConanFile):
    name = "glib-gir"
    description = "GObject Introspection data for GLib"
    topics = "gio", "gmodule", "gnome", "gobject", "gir", "introspection"
    homepage = "https://gitlab.gnome.org/GNOME/glib"
    license = "LGPL-2.1-or-later"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("gobject-introspection/[^1.82]")
        self.requires("zlib-ng/[^2.0]")
        self.requires("libffi/[^3.4.4]")
        self.requires("pcre2/[^10.42]")
        if is_apple_os(self):
            self.requires("libiconv/[^1.17]")
        # just to ensure that the versions match
        self.requires(f"glib/{self.version}", headers=False, libs=False, options={"shared": True})

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("gobject-introspection/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "meson.build", "subdir('fuzzing')", "")
        replace_in_file(self, "meson.build", "subdir('po')", "")
        replace_in_file(self, "meson.build",
                        "dependency('intl', required: false)",
                        "dependency('intl', required: true)")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["introspection"] = "enabled"
        tc.project_options["selinux"] = "disabled"
        tc.project_options["libmount"] = "disabled"
        tc.project_options["tests"] = "false"
        tc.project_options["libelf"] = "disabled"
        tc.project_options["xattr"] = "false"
        tc.project_options["nls"] = "disabled"
        tc.project_options["dtrace"] = "disabled"
        tc.project_options["systemtap"] = "disabled"
        tc.project_options["sysprof"] = "disabled"
        if self.settings.os == "Neutrino":
            tc.cross_build["host"]["system"] = "qnx"
            tc.c_link_args.append("-lm")
            tc.c_link_args.append("-lsocket")
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        if self.settings.os != "Linux":
            # intl has special handling in Meson - avoid that
            replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                            "dependency('intl'",
                            "dependency('gettext'")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LGPL-2.1-or-later.txt", os.path.join(self.source_folder, "LICENSES"), os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "include"))
        rmdir(self, os.path.join(self.package_folder, "bin"))
        for path in Path(self.package_folder, "lib").iterdir():
            if path.name != "girepository-1.0":
                if path.is_dir():
                    rmdir(self, path)
                else:
                    path.unlink()
        for path in Path(self.package_folder, "share").iterdir():
            if path.name != "gir-1.0":
                rmdir(self, path)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.resdirs = ["share"]

        self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
        self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
