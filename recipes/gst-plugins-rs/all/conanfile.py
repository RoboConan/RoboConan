import os
import re
from functools import cached_property, lru_cache
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps, GnuToolchain
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class GStPluginsRsConan(ConanFile):
    name = "gst-plugins-rs"
    description = "GStreamer plugins written in Rust"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs"
    topics = ("gstreamer", "multimedia", "video", "audio", "broadcasting", "framework", "media")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "webrtc_aws": [True, False],
        "webrtc_livekit": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,

        # Plugins can be enabled using the same option names as in meson_options.txt

        # webrtc plugin options
        "webrtc_aws": False,
        "webrtc_livekit": False,
    }
    languages = ["C"]

    python_requires = "conan-utils/latest"

    @staticmethod
    def _option_name(plugin):
        return plugin if not plugin.startswith("rs") else plugin[2:]

    @property
    def _bad(self):
        return self.dependencies["gst-plugins-bad"].options

    def export(self):
        copy(self, "plugins/*.yml", self.recipe_folder, self.export_folder)

    def init(self):
        options = set()
        for plugins_yml in Path(self.recipe_folder, "plugins").glob("*.yml"):
            plugins_info = yaml.safe_load(plugins_yml.read_text())
            for plugin, info in plugins_info.items():
                options.update(info.get("options", [self._option_name(plugin)]))
        options = sorted(options)
        self.options.update(
            {option: [True, False] for option in options},
            {option: False for option in options}
        )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        # Enable some more commonly useful plugins, so we have something to build by default
        self.options.rtp = True
        self.options.rtsp = True

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.settings.os == "Windows":
            # static build fails with an internal linker error on Windows
            del self.options.shared
            self.package_type = "shared-library"
        self.options["gstreamer"].shared = self.options.get_safe("shared", True)
        if self.options.webrtc:
            self.options["gst-plugins-bad"].webrtc = True
            self.options["gst-plugins-bad"].dtls = True
            self.options["gst-plugins-bad"].sctp = True
            self.options["gst-plugins-bad"].srtp = True
            self.options.rtp = True
        else:
            self.options.rm_safe("webrtc_aws")
            self.options.rm_safe("webrtc_livekit")

    def layout(self):
        basic_layout(self, src_folder="src")

    @cached_property
    def _plugins(self):
        version = Version(self.version)
        return yaml.safe_load(Path(self.recipe_folder, "plugins", f"{version.major}.{version.minor}.yml").read_text())

    def _is_enabled(self, plugin):
        required_options = self._plugins[plugin].get("options", [self._option_name(plugin)])
        return all(self.options.get_safe(opt, False) for opt in required_options)

    @lru_cache
    def _plugin_reqs(self, plugin):
        reqs = []
        for req in self._plugins[plugin]["requires"]:
            m = re.fullmatch("gstreamer-(.+)-1.0", req)
            if m and m[1] in _gstreamer_libs:
                reqs.append(f"gstreamer::{m[0]}")
            elif m and m[1] in _plugins_base_libs:
                reqs.append(f"gst-plugins-base::{m[0]}")
            elif m and m[1] in _plugins_bad_libs:
                reqs.append(f"gst-plugins-bad::{m[0]}")
            else:
                reqs.append(req)
        return reqs

    @cached_property
    def _all_reqs(self):
        reqs = set()
        for plugin in self._plugins:
            if self._is_enabled(plugin):
                reqs.update(r.split("::")[0] for r in self._plugin_reqs(plugin) if "::" in r)
        return reqs

    @cached_property
    def _all_options(self):
        options = set()
        for plugins_yml in Path(self.recipe_folder, "plugins").glob("*.yml"):
            plugins_info = yaml.safe_load(plugins_yml.read_text())
            for plugin, info in plugins_info.items():
                options.update(info.get("options", [self._option_name(plugin)]))
        return options

    def requirements(self):
        reqs = self._all_reqs
        self.requires(f"gstreamer/{self.version}", transitive_headers=True, transitive_libs=True)
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        if "gst-plugins-base" in reqs:
            self.requires(f"gst-plugins-base/{self.version}", transitive_headers=True, transitive_libs=True)
        if "gst-plugins-bad" in reqs:
            self.requires(f"gst-plugins-bad/{self.version}", transitive_headers=True, transitive_libs=True)

        if "cairo" in reqs:
            self.requires("cairo/[^1.18.0]")
        if "dav1d" in reqs:
            self.requires("dav1d/[^1.4.3]")
        if "gtk" in reqs:
            self.requires("gtk/[^4.15]")
        if "openssl" in reqs:
            self.requires("openssl/[>=1.1 <4]")
        if "pango" in reqs:
            self.requires("pango/[^1.54.0]", options={"with_cairo": True})
        if "libsodium" in reqs:
            self.requires("libsodium/[^1.0.20]")
        if "libwebp" in reqs:
            self.requires("libwebp/[^1.3.2]")

    def validate(self):
        if not self.dependencies["glib"].options.shared and self.options.get_safe("shared", True):
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration("shared GStreamer cannot link to static GLib")
        if self.options.get_safe("shared", True) != self.dependencies["gstreamer"].options.shared:
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration("GStreamer and GstPlugins must be either all shared, or all static")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        self.tool_requires("glib/<host_version>")
        self.tool_requires("rust/[^1.72]")
        self.tool_requires("cargo-c/[^0.10]")
        if self.options.rav1e:
            self.tool_requires("nasm/[*]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _define_rust_env(self, env, scope="host", cflags=None):
        target = self.conf.get(f"user.rust:target_{scope}", check_type=str).replace("-", "_")
        cc = GnuToolchain(self).extra_env.vars(self).get("CC" if scope == "host" else "CC_FOR_BUILD", "cc")
        env.define_path(f"CARGO_TARGET_{target.upper()}_LINKER", cc)
        env.define_path(f"CC_{target}", cc)
        if cflags:
            env.append(f"CFLAGS_{target}", cflags)

    def generate(self):
        env = Environment()
        self._define_rust_env(env, "host")
        if cross_building(self):
            self._define_rust_env(env, "build")
        env.define_path("CARGO_HOME", os.path.join(self.build_folder, "cargo"))
        env.vars(self).save_script("cargo_paths")

        def feature(v):
            return "enabled" if v else "disabled"

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        for opt in self._all_options:
            tc.project_options[opt] = feature(self.options.get_safe(opt))
        tc.project_options["doc"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["sodium-source"] = "system"
        tc.project_options["webrtc-aws"] = feature(self.options.get_safe("webrtc_aws"))
        tc.project_options["webrtc-livekit"] = feature(self.options.get_safe("webrtc_livekit"))
        tc.generate()

        if cross_building(self):
            rust_target = self.conf.get(f"user.rust:target_host", check_type=str)
            replace_in_file(self, "conan_meson_cross.ini",
                            "[binaries]",
                            f"[binaries]\nrust = ['rustc', '--target', '{rust_target}']")

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        if self.settings_build.os == "Windows":
            # shlex.split without posix=False mangles Windows directory separators
            # https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs/-/issues/696
            replace_in_file(self, os.path.join(self.source_folder, "cargo_wrapper.py"),
                            "shlex.split(",
                            "shlex.split(posix=False, s=")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE-*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "gstreamer-1.0", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        gst_plugins = []

        if self.options.get_safe("shared", True):
            self.runenv_info.define_path("GST_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "gstreamer-1.0"))

        def _define_plugin(name, extra_requires):
            name = f"gst{name}"
            component = self.cpp_info.components[name]
            component.requires = [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "glib::gobject-2.0",
                "glib::glib-2.0",
                "glib::gio-2.0",
            ] + extra_requires
            component.includedirs = []
            component.bindirs = []
            component.resdirs = ["share"]
            if self.options.get_safe("shared", True):
                component.bindirs.append(os.path.join("lib", "gstreamer-1.0"))
            else:
                component.libs = [name]
                component.libdirs = [os.path.join("lib", "gstreamer-1.0")]
                if self.settings.os in ["Linux", "FreeBSD"]:
                    component.system_libs = ["m"]
            gst_plugins.append(name)
            return component

        for plugin, info in self._plugins.items():
            if self._is_enabled(plugin):
                _define_plugin(plugin, self._plugin_reqs(plugin))


_gstreamer_libs = {
    "base",
    "check",
    "controller",
    "net",
}
_plugins_base_libs = {
    "allocators",
    "app",
    "audio",
    "fft",
    "gl",
    "gl-egl",
    "gl-prototypes",
    "gl-wayland",
    "gl-x11",
    "pbutils",
    "plugins-base",
    "riff",
    "rtp",
    "rtsp",
    "sdp",
    "tag",
    "video",
}
_plugins_bad_libs = {
    "adaptivedemux",
    "analytics",
    "bad-audio",
    "bad-base-camerabinsrc",
    "codecparsers",
    "codecs",
    "cuda",
    "d3d11",
    "downloader",
    "dxva",
    "insertbin",
    "isoff",
    "mpegts",
    "mse",
    "opencv",
    "photography",
    "play",
    "player",
    "sctp",
    "transcoder",
    "va",
    "vulkan",
    "vulkan-wayland",
    "vulkan-xcb",
    "wayland",
    "webrtc",
    "webrtc-nice",
    "winrt",
}
