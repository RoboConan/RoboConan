import io
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv, Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import is_msvc
from conan.tools.system.package_manager import Apt

required_conan_version = ">=2.4"


class GtkConan(ConanFile):
    name = "gtk"
    description = "GTK is a multi-platform toolkit for creating graphical user interfaces"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gtk.org"
    topics = ("gui", "widgets", "gnome")

    # The upstream meson file does not create a static library
    # See https://github.com/GNOME/gtk/commit/14f0a0addb9a195bad2f8651f93b95450b186bd6
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "i18n": [True, False],
        "enable_broadway_backend": [True, False],
        "with_wayland": [True, False],
        "with_x11": [True, False],
        "with_vulkan": [True, False],
        "with_introspection": [True, False],
        # Only available as system libs
        "with_gstreamer": [True, False],
        "with_cups": [True, False],
        "with_cpdb": [True, False],
        "with_cloudproviders": [True, False],
        "with_tracker": [True, False],
        "with_iso_codes": [True, False],
        # Unavailable since v4.13.7
        "with_ffmpeg": [True, False],
    }
    default_options = {
        "i18n": False,
        "enable_broadway_backend": False,
        "with_wayland": True,
        "with_x11": True,
        "with_vulkan": True,
        "with_introspection": False,
        "with_gstreamer": False,
        "with_cups": False,
        "with_cpdb": False,
        "with_cloudproviders": False,
        "with_tracker": False,
        "with_iso_codes": False,
        "with_ffmpeg": False,
    }
    languages = ["C"]
    no_copy_source = True

    python_requires = "conan-utils/latest"

    def config_options(self):
        if self.settings.os == "Windows":
            # Fix duplicate definitions of DllMain
            self.options["gdk-pixbuf"].shared = True
            # Fix segmentation fault
            self.options["cairo"].shared = True
        # Vulkan backend is enabled for all platforms except Apple OS-s,
        # which default to a macOS backend instead
        self.options.with_vulkan = not is_apple_os(self)
        self.options["pango"].with_cairo = True
        self.options["pango"].with_freetype = True
        self.options["pango"].with_fontconfig = True
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_wayland
            del self.options.with_x11

    def configure(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.options["cairo"].with_xlib = self.options.with_x11
            self.options["cairo"].with_xlib_xrender = self.options.with_x11
            self.options["cairo"].with_xcb = self.options.with_x11
            self.options["pango"].with_xft = self.options.with_x11
            self.options["libepoxy"].x11 = self.options.with_x11
            self.options["libepoxy"].glx = self.options.with_x11
            self.options["libepoxy"].egl = self.options.with_wayland
            if self.options.with_wayland:
                self.options["xkbcommon"].with_x11 = self.options.with_x11
                self.options["xkbcommon"].with_wayland = True

        if self.options.with_introspection:
            for dep in self._introspections_deps:
                self.options[dep].with_introspection = True

    @property
    def _introspections_deps(self):
        # Dependencies that must have introspection enabled as well if with_introspection is enabled
        # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gtk/meson.build?ref_type=tags#L1146
        # cairo-1.0 and Gio-2.0 are provided by gobject-introspection
        return ["gdk-pixbuf", "pango", "graphene"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # INFO: https://gitlab.gnome.org/GNOME/gtk/-/blob/4.10.0/gdk/gdktypes.h?ref_type=tags#L34-38
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_introspection:
            self.requires("gobject-introspection/[^1.82]", options={"build_introspection_data": True})
            self.requires("glib-gir/[^2.82]")
        # INFO: https://gitlab.gnome.org/GNOME/gtk/-/blob/4.10.0/gdk/gdkpixbuf.h?ref_type=tags#L32-33
        # Note: gdkpixbuf.h is deprecated in newer versions
        self.requires("gdk-pixbuf/[^2.42.10]", transitive_headers=True, transitive_libs=True)
        self.requires("pango/[^1.54.0]", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/[^1.18.0]", transitive_headers=True, transitive_libs=True)
        # INFO: https://gitlab.gnome.org/GNOME/gtk/-/blob/4.10.0/gsk/gsktypes.h#L25
        self.requires("graphene/1.10.8", transitive_headers=True, transitive_libs=True)
        self.requires("libepoxy/1.5.10")
        self.requires("fribidi/[^1.0.13]")
        self.requires("harfbuzz/[*]")
        self.requires("libpng/[~1.6]")
        self.requires("libtiff/[>=4.5 <5]")
        self.requires("libjpeg-meta/latest")
        if self.settings.os == "Linux":
            self.requires("libdrm/[~2.4.119]")
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22.0]")
            self.requires("xkbcommon/[^1.6.0]")
            # workaround for [replace_requires] bug of not propagating egl from libepoxy correctly,
            # when egl/system is replaced with libglvnd
            self.requires("egl/system")
        if self.options.get_safe("with_x11"):
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.10.0/gdk/x11/gdkx11display.h#L35-36
            # Only the xorg::x11 component actually requires transitive headers/libs.
            self.requires("xorg/system", transitive_headers=True, transitive_libs=True)
            self.requires("fontconfig/[^2.15.0]")
        if self.options.with_vulkan:
            self.requires("vulkan-loader/[^1.3.239.0]")
        if self.options.get_safe("with_ffmpeg"):
            self.requires("ffmpeg/[>=6]")

        if self.options.with_gstreamer:
            self.requires("gst-plugins-base/[^1.24]")
            self.requires("gst-plugins-bad/[^1.24]")

        # TODO: fix libintl support on macOS by using gnuintl from gettext
        # if self.settings.os != "Linux":
        #     # for Linux, gettext is provided by libc
        #     self.requires("gettext/[>=0.21 <1]", transitive_headers=True, transitive_libs=True)

        # TODO: iso-codes
        # TODO: tracker-sparql-3.0
        # TODO: cloudproviders
        # TODO: sysprof-capture-4
        # TODO: cpdb-frontend
        # TODO: cups, colord

    def validate(self):
        if is_msvc(self):
            if not self.dependencies["gdk-pixbuf"].options.shared:
                raise ConanInvalidConfiguration("MSVC build requires shared gdk-pixbuf")
            if not self.dependencies["cairo"].options.shared:
                raise ConanInvalidConfiguration("MSVC build requires shared cairo")
        if self.settings.os in ["Linux", "FreeBSD"]:
            if not self.options.with_x11 and not self.options.with_wayland:
                # Fails with 'Problem encountered: No backends enabled' otherwise
                raise ConanInvalidConfiguration("At least one of 'with_x11' or 'with_wayland' options must be enabled")
            if self.options.with_x11 and not self.dependencies["cairo"].options.with_xlib:
                raise ConanInvalidConfiguration("cairo must be built with '-o cairo/*:with_xlib=True' when 'with_x11' is enabled")
        if not self.dependencies["pango"].options.with_freetype:
            raise ConanInvalidConfiguration("pango must be built with '-o pango/*:with_freetype=True'")
        if self.options.with_introspection:
            for dep in self._introspections_deps:
                if not self.dependencies[dep].options.with_introspection:
                    raise ConanInvalidConfiguration(f"{dep} must be built with introspection enabled (-o {dep}/*:with_introspection=True)")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("glib/<host_version>")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        self.tool_requires("libxml2/[^2.12.5]")  # for xmllint
        self.tool_requires("sassc/3.6.2")
        if self.options.with_vulkan:
            self.tool_requires("shaderc/2025.2")  # for glslc
        if self.options.get_safe("with_wayland"):
            self.tool_requires("wayland/<host_version>")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    @property
    def _apt_packages(self):
        packages = []
        if self.options.with_cups:
            packages.append("libcups2-dev")
            packages.append("libcolord-dev")
        if self.options.with_cpdb:
            packages.append("libcpdb-frontend-dev")
        if self.options.with_cloudproviders:
            packages.append("libcloudproviders-dev")
        if self.options.with_tracker:
            packages.append("libtracker-sparql-3.0-dev")
        if self.options.with_iso_codes:
            packages.append("iso-codes")
        return packages

    def system_requirements(self):
        Apt(self).install(self._apt_packages, update=True, check=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # Required for glib-compile-resources
        if can_run(self):
            VirtualRunEnv(self).generate(scope="build")

        enabled_disabled = lambda opt: "enabled" if opt else "disabled"
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["wayland-backend"] = "true" if self.options.get_safe("with_wayland") else "false"
        tc.project_options["x11-backend"] = "true" if self.options.get_safe("with_x11") else "false"
        tc.project_options["broadway-backend"] = "true" if self.options.enable_broadway_backend else "false"
        tc.project_options["vulkan"] = enabled_disabled(self.options.with_vulkan)
        tc.project_options["media-gstreamer"] = enabled_disabled(self.options.with_gstreamer)
        tc.project_options["print-cups"] = enabled_disabled(self.options.with_cups)
        tc.project_options["colord"] = enabled_disabled(self.options.with_cups)
        tc.project_options["print-cpdb"] = enabled_disabled(self.options.with_cpdb)
        tc.project_options["cloudproviders"] = enabled_disabled(self.options.with_cloudproviders)
        tc.project_options["tracker"] = enabled_disabled(self.options.with_tracker)
        tc.project_options["introspection"] = enabled_disabled(self.options.with_introspection)

        tc.project_options["documentation"] = "false"
        tc.project_options["screenshots"] = "false"
        tc.project_options["build-demos"] = "false"
        tc.project_options["build-testsuite"] = "false"
        tc.project_options["man-pages"] = "false"
        tc.project_options["build-tests"] = "false"
        tc.project_options["build-examples"] = "false"

        tc.pkg_config_path = None
        tc.build_pkg_config_path = None
        tc.generate()

        deps = PkgConfigDeps(self)
        if self.options.get_safe("with_wayland"):
            deps.build_context_activated.append("wayland")
            deps.build_context_folder = os.path.join(self.generators_folder, "build")
        deps.generate()

        env = Environment()
        env.define_path("PKG_CONFIG_PATH", self.generators_folder)
        env.append_path("PKG_CONFIG_PATH", os.path.join(self.generators_folder, "build"))
        if self._apt_packages:
            env.append_path("PKG_CONFIG_PATH", self._get_system_pkg_config_paths())
        env.define_path("PKG_CONFIG_FOR_BUILD", self.conf.get("tools.gnu:pkg_config", default="pkgconf", check_type=str))
        env.define_path("PKG_CONFIG_PATH_FOR_BUILD", os.path.join(self.generators_folder, "build"))
        env.vars(self).save_script("conan_pkg_config_path")

    def _get_system_pkg_config_paths(self):
        # Global PKG_CONFIG_PATH is generally not filled by default, so ask for the default paths from pkg-config instead.
        # Assumes that pkg-config is installed system-wide.
        pkg_config = self.conf.get("tools.gnu:pkg_config", default="pkg-config", check_type=str)
        output = io.StringIO()
        self.run(f"{pkg_config} --variable pc_path pkg-config", output, scope=None)
        return output.getvalue().strip()

    def build(self):
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
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"), recursive=True)
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"), recursive=True)
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/meson.build?ref_type=tags#L841-883
        self.cpp_info.components["gtk4"].set_property("pkg_config_name", "gtk4")
        self.cpp_info.components["gtk4"].libs = ["gtk-4"]
        self.cpp_info.components["gtk4"].includedirs.append(os.path.join("include", "gtk-4.0"))
        self.cpp_info.components["gtk4"].resdirs = ["share", "etc"]
        # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gdk/meson.build#L221-240
        # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gtk/meson.build#L1000-1015
        self.cpp_info.components["gtk4"].requires = [
            "glib::glib-2.0",
            "glib::gmodule-2.0",
            "glib::gobject-2.0",
            "glib::gio-unix-2.0" if self.settings.os != "Windows" else "glib::gio-windows-2.0",
            "gdk-pixbuf::gdk-pixbuf",
            "cairo::cairo_",
            "cairo::cairo-gobject",
            "pango::pango_" if self.settings.os != "Windows" else "pango::pangowin32",
            "pango::pangocairo",
            "fribidi::fribidi",
            "graphene::graphene-gobject-1.0",
            "harfbuzz::harfbuzz_",
            "harfbuzz::subset",
            "libepoxy::libepoxy",
            "libjpeg-meta::jpeg",
            "libpng::libpng",
            "libtiff::tiff",
        ]
        if self.settings.os == "Linux":
            self.cpp_info.components["gtk4"].requires.append("libdrm::libdrm")
        if self.options.with_vulkan:
            self.cpp_info.components["gtk4"].requires.append("vulkan-loader::vulkan-loader")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["gtk4"].system_libs = ["m", "rt"]
        elif self.settings.os == "Windows":
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gtk/meson.build#L1038-1044
            self.cpp_info.components["gdk-3.0"].system_libs = ["advapi32", "comctl32", "crypt32", "dwmapi", "imm32", "setupapi", "winmm"]

        if self.options.with_gstreamer:
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/modules/media/meson.build#L11
            self.cpp_info.components["gtk4"].requires.extend([
                "gst-plugins-bad::gstreamer-player-1.0",
                "gst-plugins-base::gstreamer-gl-1.0",
                "gst-plugins-base::gstreamer-allocators-1.0",
            ])
        if self.options.get_safe("with_ffmpeg"):
            self.cpp_info.components["gtk4"].requires.append("ffmpeg::ffmpeg")

        # TODO:
        # if self.options.with_cups:
        #     self.cpp_info.components["gtk4"].requires.extend(["cups::cups", "colord::colord"])
        # if self.options.with_cpdb:
        #     self.cpp_info.components["gtk4"].requires.append("cpdb::cpdb")
        # if self.options.with_cloudproviders:
        #     self.cpp_info.components["gtk4"].requires.append("cloudproviders::cloudproviders")
        # if self.options.with_tracker:
        #     self.cpp_info.components["gtk4"].requires.append("tracker-sparql::tracker-sparql")

        if self.options.enable_broadway_backend:
            self.cpp_info.components["gtk4-broadway"].set_property("pkg_config_name", "gtk4-broadway")
            self.cpp_info.components["gtk4-broadway"].requires = ["gtk4"]
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gdk/broadway/meson.build#L66
            if self.settings.os == "Windows":
                self.cpp_info.components["gtk4"].system_libs.append("ws2_32")

        # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/meson.build?ref_type=tags#L841-883
        if self.options.get_safe("with_x11"):
            self.cpp_info.components["gtk4-x11"].set_property("pkg_config_name", "gtk4-x11")
            self.cpp_info.components["gtk4-x11"].requires = ["gtk4"]
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gdk/x11/meson.build#L63-73
            self.cpp_info.components["gtk4"].requires.extend([
                "xorg::xrandr",
                "xorg::x11",
                "xorg::xrender",
                "xorg::xi",
                "xorg::xext",
                "xorg::xcursor",
                "xorg::xdamage",
                "xorg::xfixes",
                "xorg::xinerama",
                "fontconfig::fontconfig",
            ])

        if self.options.get_safe("with_wayland"):
            self.cpp_info.components["gtk4-wayland"].set_property("pkg_config_name", "gtk4-wayland")
            self.cpp_info.components["gtk4-wayland"].requires = ["gtk4"]
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gdk/wayland/meson.build#L44-50
            self.cpp_info.components["gtk4"].requires.extend([
                "xkbcommon::xkbcommon",
                "wayland::wayland-client",
                "wayland::wayland-egl",
                "egl::egl",
            ])

        if is_apple_os(self):
            self.cpp_info.components["gtk4-macos"].set_property("pkg_config_name", "gtk4-macos")
            self.cpp_info.components["gtk4-macos"].requires = ["gtk4"]
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gdk/macos/meson.build#L46-55
            self.cpp_info.components["gtk4"].frameworks.extend([
                "AppKit",
                "Carbon",
                "CoreVideo",
                "CoreServices",
                "Foundation",
                "IOSurface",
                "OpenGL",
                "QuartzCore",
            ])

        if self.settings.os == "Windows":
            self.cpp_info.components["gtk4-win32"].set_property("pkg_config_name", "gtk4-win32")
            self.cpp_info.components["gtk4-win32"].requires = ["gtk4"]
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/gdk/win32/meson.build#L60-64
            self.cpp_info.components["gtk4"].system_libs.extend(["hid", "opengl32"])

        if self.settings.os != "Windows":
            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/meson.build?ref_type=tags#L897-907
            self.cpp_info.components["gtk4-atspi"].set_property("pkg_config_name", "gtk4-atspi")
            self.cpp_info.components["gtk4-atspi"].requires = ["gtk4"]

            # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.15.6/meson.build?ref_type=tags#L909-919
            self.cpp_info.components["gtk4-unix-print"].set_property("pkg_config_name", "gtk4-unix-print")
            self.cpp_info.components["gtk4-unix-print"].requires = ["gtk4"]
            self.cpp_info.components["gtk4-unix-print"].includedirs.append(os.path.join("include", "gtk-4.0", "unix-print"))

        if self.options.with_introspection:
            self.cpp_info.components["gtk4"].requires.extend(["gobject-introspection::gobject-introspection", "glib-gir::glib-gir"])
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))

        # https://gitlab.gnome.org/GNOME/gtk/-/blob/4.16.7/meson.build?ref_type=tags#L862-873
        pkgconfig_variables = {
            "targets": " ".join(self._enabled_backends),
            "gtk_binary_version": "4.0.0",
            "gtk_host": f"{self._host_arch}-{self._host_os}",
        }
        extra_content = "\n".join(f"{key}={value}" for key, value in pkgconfig_variables.items())
        for _, component in self.cpp_info.components.items():
            component.set_property("pkg_config_custom_content", extra_content)

    @property
    def _enabled_backends(self):
        backends = []
        if self.options.enable_broadway_backend:
            backends.append("broadway")
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.options.with_x11:
                backends.append("x11")
            if self.options.with_wayland:
                backends.append("wayland")
        elif is_apple_os(self):
            backends.append("macos")
        elif self.settings.os == "Windows":
            backends.append("win32")
        return backends

    @property
    def _host_arch(self):
        # https://mesonbuild.com/Reference-tables.html#cpu-families
        if self.settings.arch == "armv8":
            return "aarch64"
        elif str(self.settings.arch).startswith("arm"):
            return "arm"
        return str(self.settings.arch).lower()

    @property
    def _host_os(self):
        # https://mesonbuild.com/Reference-tables.html#operating-system-names
        if is_apple_os(self):
            return "darwin"
        return str(self.settings.os).lower()
