import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.cmake import cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import MesonToolchain, Meson

required_conan_version = ">=2.4"


class LibrsvgConan(ConanFile):
    name = "librsvg"
    description = "A library to render SVG images to Cairo surfaces."
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/librsvg"
    topics = ("svg", "vector-graphics", "cairo", "gnome")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_introspection": False,
    }
    languages = ["C"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        self.options["pango"].with_cairo = True

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")
        if self.settings.os == "Windows":
            # static build fails with an internal linker error
            del self.options.shared
            self.package_type = "shared-library"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # https://gitlab.gnome.org/GNOME/librsvg/-/blob/main/ci/build-dependencies.sh#L5-13
        # All public includes are located here:
        # https://gitlab.gnome.org/GNOME/librsvg/-/blob/2.57.0/include/librsvg/rsvg.h#L30-34
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_introspection:
            self.requires("gobject-introspection/[^1.82]", options={"build_introspection_data": True})
            self.requires("glib-gir/[^2.82]")
        self.requires("freetype/[^2.13.2]")
        self.requires("fontconfig/[^2.15.0]")
        self.requires("cairo/[^1.18.0]", transitive_headers=True, transitive_libs=True)
        self.requires("harfbuzz/[*]")
        self.requires("pango/[^1.54.0]")
        self.requires("libxml2/[^2.12.5]")
        self.requires("gdk-pixbuf/[^2.42.10]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if not self.dependencies["pango"].options.with_cairo:
            raise ConanInvalidConfiguration("librsvg requires -o pango/*:with_cairo=True")

    def build_requirements(self):
        self.tool_requires("rust/[^1.72]")
        self.tool_requires("cargo-c/[*]")
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("gdk-pixbuf/<host_version>")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["tests"] = "false"
        tc.project_options["vala"] = "disabled"
        tc.project_options["docs"] = "disabled"
        if cross_building(self):
            tc.project_options["triplet"] = self.conf.get("user.rust:target_host", check_type=str)
        tc.project_options["pixbuf"] = "enabled"
        tc.project_options["introspection"] = "enabled" if self.options.with_introspection else "disabled"
        tc.project_options["avif"] = "disabled"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING.LIB", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "librsvg-2.0")
        self.cpp_info.libs = ["rsvg-2" if self.settings.os == "Windows" else "librsvg-2"]
        self.cpp_info.includedirs.append(os.path.join("include", "librsvg-2.0"))
        self.cpp_info.resdirs = ["share"]

        # https://gitlab.gnome.org/GNOME/librsvg/-/blob/2.57.0/configure.ac#L161-173
        self.cpp_info.requires = [
            "cairo::cairo_",
            "cairo::cairo-png",
            "cairo::cairo-gobject",
            "fontconfig::fontconfig",
            "freetype::freetype",
            "gdk-pixbuf::gdk-pixbuf",
            "glib::gio-2.0",
            "glib::glib-2.0",
            "harfbuzz::harfbuzz",
            "libxml2::libxml2",
            "pango::pangocairo",
        ]
        if "pangoft2" in self.dependencies["pango"].cpp_info.components:
            self.cpp_info.requires.append("pango::pangoft2")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread", "m", "dl", "rt"]

        self.runenv_info.append_path("GDK_PIXBUF_MODULEDIR", os.path.join(self.package_folder, "lib", "gdk-pixbuf-2.0", "2.10", "loaders"))

        if self.options.with_introspection:
            self.cpp_info.requires.extend(["gobject-introspection::gobject-introspection", "glib-gir::glib-gir"])
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
