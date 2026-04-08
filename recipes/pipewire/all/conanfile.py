import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class PipeWireConan(ConanFile):
    name = "pipewire"
    description = "PipeWire is a server and user space API to deal with multimedia pipelines."
    license = "MIT"
    homepage = "https://pipewire.org/"
    topics = ("audio", "graph", "pipeline", "stream", "video")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "i18n": [True, False],
        "flatpak": [True, False],
        "gsettings": [True, False],
        "raop": [True, False],
        "with_avahi": [True, False],
        "with_dbus": [True, False],
        "with_ffmpeg": [True, False],
        "with_libalsa": [True, False],
        "with_libsndfile": [True, False],
        "with_libudev": [True, False],
        "with_ncurses": [True, False],
        "with_opus": [True, False],
        "with_pulseaudio": [True, False],
        "with_readline": [True, False],
        "with_selinux": [True, False],
        "with_vulkan": [True, False],
        "with_x11": [True, False],
        "with_xfixes": [True, False],
    }
    default_options = {
        "i18n": False,
        "flatpak": True,
        "gsettings": True,
        "raop": True,
        "with_avahi": False,
        "with_dbus": False,
        "with_ffmpeg": False,
        "with_libalsa": True,
        "with_libsndfile": False,
        "with_libudev": False,
        "with_ncurses": False,
        "with_opus": False,
        "with_pulseaudio": True,
        "with_readline": False,
        "with_selinux": False,
        "with_vulkan": False,
        "with_x11": False,
        "with_xfixes": False,
    }
    languages = ["C"]

    def configure(self):
        if not self.options.with_x11:
            del self.options.with_xfixes
        if self.options.with_libalsa:
            self.options.with_libudev.value = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.flatpak or self.options.gsettings:
            self.requires("glib/[^2.70.0]")
        if self.options.raop:
            self.requires("openssl/[>=1.1 <4]")
        if self.options.with_avahi:
            self.requires("avahi/0.8")
        if self.options.with_dbus:
            self.requires("dbus/[^1.15]")
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/[>=6]")
        if self.options.with_libalsa:
            self.requires("libalsa/[^1.2.10]")
        if self.options.with_libsndfile:
            self.requires("libsndfile/[^1.2.2]")
        if self.options.with_libudev:
            self.requires("libudev/[>=255 <system]")
        if self.options.with_ncurses:
            self.requires("ncurses/[^6.4]")
        if self.options.with_opus:
            self.requires("opus/[^1.4]")
        if self.options.with_pulseaudio:
            self.requires("pulseaudio/[^17.0]")
        if self.options.with_readline:
            self.requires("readline/[^8.2]")
        if self.options.with_selinux:
            self.requires("libselinux/3.6")
        if self.options.with_vulkan:
            self.requires("linux-headers-generic/[^6.5]")
            self.requires("libdrm/[~2.4.119]")
            self.requires("vulkan-headers/[^1.3.239.0]")
            self.requires("vulkan-loader/[^1.3.239.0]")
        if self.options.with_x11:
            self.requires("xorg/system")

    def validate(self):
        if self.settings.os not in ["FreeBSD", "Linux"]:
            raise ConanInvalidConfiguration(f"{self.name} not supported for {self.settings.os}")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        def feature(option, default=False):
            return "enabled" if self.options.get_safe(option, default=default) else "disabled"

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["alsa"] = feature("with_libalsa")
        tc.project_options["avahi"] = feature("with_avahi")
        tc.project_options["avb"] = "enabled" if self.settings.os == "Linux" else "disabled"
        tc.project_options["bluez5"] = "disabled"
        tc.project_options["bluez5-codec-aac"] = "disabled"
        tc.project_options["bluez5-codec-aptx"] = "disabled"
        tc.project_options["bluez5-codec-g722"] = "disabled"
        tc.project_options["bluez5-codec-lc3"] = "disabled"
        tc.project_options["bluez5-codec-lc3plus"] = "disabled"
        tc.project_options["bluez5-codec-ldac"] = "disabled"
        tc.project_options["bluez5-codec-opus"] = "disabled"
        tc.project_options["compress-offload"] = feature("with_libalsa")
        tc.project_options["dbus"] = feature("with_dbus")
        tc.project_options["docs"] = "disabled"
        tc.project_options["ebur128"] = "disabled"
        tc.project_options["echo-cancel-webrtc"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["ffmpeg"] = feature("with_ffmpeg")
        tc.project_options["flatpak"] = feature("flatpak")
        tc.project_options["gsettings"] = feature("gsettings")
        tc.project_options["gsettings-pulse-schema"] = feature("gsettings")
        tc.project_options["gstreamer"] = "disabled"
        tc.project_options["gstreamer-device-provider"] = "disabled"
        tc.project_options["jack"] = "disabled"
        tc.project_options["legacy-rtkit"] = False
        tc.project_options["libcamera"] = "disabled"
        tc.project_options["libcanberra"] = "disabled"
        tc.project_options["libffado"] = "disabled"
        tc.project_options["libmysofa"] = "disabled"
        tc.project_options["libpulse"] = feature("with_pulseaudio")
        tc.project_options["libusb"] = "disabled"
        tc.project_options["logind"] = "disabled"
        tc.project_options["lv2"] = "disabled"
        tc.project_options["man"] = "disabled"
        tc.project_options["opus"] = feature("with_opus")
        tc.project_options["pipewire-alsa"] = feature("with_libalsa")
        tc.project_options["pipewire-jack"] = "disabled"
        tc.project_options["pipewire-v4l2"] = "disabled"
        tc.project_options["pw-cat"] = feature("with_libsndfile")
        tc.project_options["pw-cat-ffmpeg"] = feature("with_ffmpeg")
        tc.project_options["raop"] = feature("raop")
        tc.project_options["readline"] = feature("with_readline")
        tc.project_options["roc"] = "disabled"
        tc.project_options["sdl2"] = "disabled"
        tc.project_options["selinux"] = feature("with_selinux")
        tc.project_options["session-managers"] = []
        tc.project_options["snap"] = "disabled"
        tc.project_options["sndfile"] = feature("with_libsndfile")
        tc.project_options["spa-plugins"] = "enabled"
        tc.project_options["systemd"] = "disabled"
        tc.project_options["systemd-user-service"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["udev"] = feature("with_libudev", True)
        tc.project_options["udevrulesdir"] = "lib/udev/rules.d"
        tc.project_options["vulkan"] = feature("with_vulkan")
        tc.project_options["v4l2"] = "disabled"
        tc.project_options["x11"] = feature("with_x11")
        tc.project_options["x11-xfixes"] = feature("with_xfixes")
        # Workaround an strict-prototypes error caused by the readline include file: readline/rltypedefs.h
        # todo Report this issue upstream.
        tc.extra_cflags.append("-Wno-error=strict-prototypes")
        # This appears to be an issue that crops up when using Avahi and libpulse involving the malloc_info and malloc_trim functions.
        tc.extra_cflags.append("-Wno-error=implicit-function-declaration")
        if self.options.with_vulkan:
            for includedir in self.dependencies["linux-headers-generic"].cpp_info.includedirs:
                tc.extra_cflags.append(f"-I{includedir}")
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        if not self.options.i18n:
            save(self, os.path.join(self.source_folder, "po", "meson.build"), "")
        meson = Meson(self)
        meson.configure()
        meson.build()

    @property
    def _libpipewire_api_version_txt(self):
        return os.path.join(self.package_folder, "share", "conan", "libpipewire-api-version.txt")

    @property
    def _libspa_api_version_txt(self):
        return os.path.join(self.package_folder, "share", "conan", "libspa-api-version.txt")

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        pkconfig_dir = Path(self.package_folder, "lib", "pkgconfig")
        libpipewire_api_version = next(pkconfig_dir.glob("libpipewire-*.pc")).stem.split("-")[1]
        libspa_api_version = next(pkconfig_dir.glob("libspa-*.pc")).stem.split("-")[1]
        save(self, self._libpipewire_api_version_txt, libpipewire_api_version)
        save(self, self._libspa_api_version_txt, libspa_api_version)
        rmdir(self, pkconfig_dir)
        fix_apple_shared_install_name(self)

    def package_info(self):
        libpipewire_api_version = load(self, self._libpipewire_api_version_txt).strip()
        libspa_api_version = load(self, self._libspa_api_version_txt).strip()

        self.runenv_info.define("PIPEWIRE_CONFIG_DIR", os.path.join(self.package_folder, "share", "pipewire"))
        self.runenv_info.define("PIPEWIRE_MODULE_DIR", os.path.join(self.package_folder, "lib", f"pipewire-{libpipewire_api_version}"))
        self.runenv_info.define("SPA_PLUGIN_DIR", os.path.join(self.package_folder, "lib", f"spa-{libspa_api_version}"))

        if self.options.gsettings:
            self.runenv_info.append_path("GSETTINGS_SCHEMA_DIR", os.path.join(self.package_folder, "share", "glib-2.0", "schemas"))

        if self.options.with_libalsa:
            self.runenv_info.define("ACP_PATHS_DIR", os.path.join(self.package_folder, "share", "alsa-card-profile", "mixer", "paths"))
            self.runenv_info.define("ACP_PROFILES_DIR", os.path.join(self.package_folder, "share", "alsa-card-profile", "mixer", "profiles-sets"))
            self.runenv_info.prepend_path("ALSA_PLUGIN_DIR", os.path.join(self.package_folder, "lib", "alsa-lib"))

        self.cpp_info.components["libpipewire"].set_property("pkg_config_name", f"libpipewire-{libpipewire_api_version}")
        self.cpp_info.components["libpipewire"].libs = [f"pipewire-{libpipewire_api_version}"]
        self.cpp_info.components["libpipewire"].includedirs = [os.path.join(self.package_folder, "include", f"pipewire-{libpipewire_api_version}")]
        self.cpp_info.components["libpipewire"].resdirs = ["etc", "share"]
        self.cpp_info.components["libpipewire"].defines = ["_REENTRANT"]
        self.cpp_info.components["libpipewire"].set_property("pkg_config_custom_content", f"moduledir=${{libdir}}/pipewire-{libpipewire_api_version}")
        self.cpp_info.components["libpipewire"].requires = ["libspa"]
        if self.options.flatpak:
            self.cpp_info.components["libpipewire"].requires.append("glib::glib-2.0")
        if self.options.gsettings:
            self.cpp_info.components["libpipewire"].requires.append("glib::gio-2.0")
        if self.options.raop:
            self.cpp_info.components["libpipewire"].requires.extend(["openssl::crypto", "openssl::ssl"])
        if self.options.with_avahi:
            self.cpp_info.components["libpipewire"].requires.append("avahi::client")
        if self.options.with_dbus:
            self.cpp_info.components["libpipewire"].requires.append("dbus::dbus")
        if self.options.with_libalsa:
            self.cpp_info.components["libpipewire"].requires.append("libalsa::libalsa")
        if self.options.with_libsndfile:
            self.cpp_info.components["libpipewire"].requires.append("libsndfile::libsndfile")
        if self.options.with_opus:
            self.cpp_info.components["libpipewire"].requires.append("opus::opus")
        if self.options.with_pulseaudio:
            self.cpp_info.components["libpipewire"].requires.append("pulseaudio::pulse")
        if self.options.with_selinux:
            self.cpp_info.components["libpipewire"].requires.append("libselinux::selinux")
        if self.options.with_x11:
            self.cpp_info.components["libpipewire"].requires.append("xorg::x11-xcb")
            if self.options.with_xfixes:
                self.cpp_info.components["libpipewire"].requires.append("xorg::xfixes")

        self.cpp_info.components["libspa"].set_property("pkg_config_name", f"libspa-{libspa_api_version}")
        self.cpp_info.components["libspa"].includedirs = [os.path.join(self.package_folder, "include", f"spa-{libspa_api_version}")]
        self.cpp_info.components["libspa"].defines = ["_REENTRANT"]
        self.cpp_info.components["libspa"].set_property("pkg_config_custom_content", f"plugindir=${{libdir}}/spa-{libspa_api_version}")
        if self.options.with_libalsa:
            self.cpp_info.components["libspa"].requires.append("libalsa::libalsa")
        if self.options.with_dbus:
            self.cpp_info.components["libspa"].requires.append("dbus::dbus")
        if self.options.with_ffmpeg:
            self.cpp_info.components["libspa"].requires.append("ffmpeg::avcodec")
        if self.options.with_libsndfile:
            self.cpp_info.components["libspa"].requires.append("libsndfile::libsndfile")
        if self.options.with_libudev:
            self.cpp_info.components["libspa"].requires.append("libudev::libudev")
        if self.options.with_vulkan:
            self.cpp_info.components["libspa"].requires.extend([
                "libdrm::libdrm_libdrm",
                "linux-headers-generic::linux-headers-generic",
                "vulkan-headers::vulkan-headers",
                "vulkan-loader::vulkan-loader",
            ])

        self.cpp_info.components["tools"].requires = ["libpipewire"]
        # pw-cat
        if self.options.with_ffmpeg:
            self.cpp_info.components["tools"].requires.extend(["ffmpeg::avcodec", "ffmpeg::avformat", "ffmpeg::avutil"])
        if self.options.with_libsndfile:
            self.cpp_info.components["tools"].requires.append("libsndfile::libsndfile")
        # pw-top
        if self.options.with_ncurses:
            self.cpp_info.components["tools"].requires.append("ncurses::libcurses")
        # pw-cli
        if self.options.with_readline:
            self.cpp_info.components["tools"].requires.append("readline::readline")
