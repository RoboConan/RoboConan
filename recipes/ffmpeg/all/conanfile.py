import io
import os
import re
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools import CppInfo
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import check_min_vs, is_msvc, unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class FFMpegConan(ConanFile):
    name = "ffmpeg"
    description = "A complete, cross-platform solution to record, convert and stream audio and video"
    # https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md
    license = "LGPL-2.1-or-later"
    homepage = "https://ffmpeg.org"
    topics = ("multimedia", "audio", "video", "encoder", "decoder", "encoding", "decoding",
              "transcoding", "multiplexer", "demultiplexer", "streaming")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "avdevice": [True, False],
        "avcodec": [True, False],
        "avformat": [True, False],
        "swresample": [True, False],
        "swscale": [True, False],
        "postproc": [True, False],
        "avfilter": [True, False],
        "with_asm": [True, False],
        "with_zlib": [True, False],
        "with_bzip2": [True, False],
        "with_lzma": [True, False],
        "with_libiconv": [True, False],
        "with_freetype": [True, False],
        "with_libxml2": [True, False],
        "with_fontconfig": [True, False],
        "with_fribidi": [True, False],
        "with_harfbuzz": [True, False],
        "with_libjxl": [True, False],
        "with_openjpeg": [True, False],
        "with_openh264": [True, False],
        "with_opus": [True, False],
        "with_vorbis": [True, False],
        "with_zeromq": [True, False],
        "with_sdl": [True, False],
        "with_libx264": [True, False],
        "with_libx265": [True, False],
        "with_libvpx": [True, False],
        "with_libmp3lame": [True, False],
        "with_liboapv": [True, False],
        "with_libfdk_aac": [True, False],
        "with_libwebp": [True, False],
        "with_ssl": [False, "openssl", "securetransport"],
        "with_libalsa": [True, False],
        "with_pulse": [True, False],
        "with_sndio": [True, False],
        "with_vaapi": [True, False],
        "with_vdpau": [True, False],
        "with_vulkan": [True, False],
        "with_xcb": [True, False],
        "with_soxr": [True, False],
        "with_appkit": [True, False],
        "with_avfoundation": [True, False],
        "with_coreimage": [True, False],
        "with_audiotoolbox": [True, False],
        "with_videotoolbox": [True, False],
        "with_programs": [True, False],
        "with_libsvtav1": [True, False],
        "with_libaom": [True, False],
        "with_libdav1d": [True, False],
        "with_libdrm": [True, False],
        "with_jni": [True, False],
        "with_mediacodec": [True, False],
        "with_xlib": [True, False],
        "with_ffnvcodec": [True, False],
        "with_cuda": [True, False],
        "with_whisper": [True, False],
        "disable_everything": [True, False],
        "disable_all_encoders": [True, False],
        "disable_encoders": [None, "ANY"],
        "enable_encoders": [None, "ANY"],
        "disable_all_decoders": [True, False],
        "disable_decoders": [None, "ANY"],
        "enable_decoders": [None, "ANY"],
        "disable_all_hardware_accelerators": [True, False],
        "disable_hardware_accelerators": [None, "ANY"],
        "enable_hardware_accelerators": [None, "ANY"],
        "disable_all_muxers": [True, False],
        "disable_muxers": [None, "ANY"],
        "enable_muxers": [None, "ANY"],
        "disable_all_demuxers": [True, False],
        "disable_demuxers": [None, "ANY"],
        "enable_demuxers": [None, "ANY"],
        "disable_all_parsers": [True, False],
        "disable_parsers": [None, "ANY"],
        "enable_parsers": [None, "ANY"],
        "disable_all_bitstream_filters": [True, False],
        "disable_bitstream_filters": [None, "ANY"],
        "enable_bitstream_filters": [None, "ANY"],
        "disable_all_protocols": [True, False],
        "disable_protocols": [None, "ANY"],
        "enable_protocols": [None, "ANY"],
        "disable_all_devices": [True, False],
        "disable_all_input_devices": [True, False],
        "disable_input_devices": [None, "ANY"],
        "enable_input_devices": [None, "ANY"],
        "disable_all_output_devices": [True, False],
        "disable_output_devices": [None, "ANY"],
        "enable_output_devices": [None, "ANY"],
        "disable_all_filters": [True, False],
        "disable_filters": [None, "ANY"],
        "enable_filters": [None, "ANY"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "avdevice": True,
        "avcodec": True,
        "avformat": True,
        "swresample": True,
        "swscale": True,
        "postproc": True,
        "avfilter": True,
        "with_asm": True,
        "with_zlib": True,
        "with_bzip2": True,
        "with_lzma": True,
        "with_libiconv": True,
        "with_freetype": True,
        "with_libxml2": False,
        "with_fontconfig": False,
        "with_fribidi": False,
        "with_harfbuzz": False,
        "with_libjxl": False,
        "with_openjpeg": True,
        "with_openh264": True,
        "with_opus": True,
        "with_vorbis": True,
        "with_zeromq": False,
        "with_sdl": False,
        "with_libx264": True,  # GPL
        "with_libx265": True,  # GPL
        "with_libvpx": True,
        "with_libmp3lame": True,
        "with_liboapv": False,
        "with_libfdk_aac": True,  # non-free
        "with_libwebp": True,
        "with_ssl": "openssl",
        "with_libalsa": True,
        "with_pulse": True,
        "with_sndio": False,
        "with_vaapi": True,
        "with_vdpau": True,
        "with_vulkan": False,
        "with_xcb": True,
        "with_soxr": False,
        "with_appkit": True,
        "with_avfoundation": True,
        "with_coreimage": True,
        "with_audiotoolbox": True,
        "with_videotoolbox": True,
        "with_programs": True,
        "with_libsvtav1": True,
        "with_libaom": True,
        "with_libdav1d": True,
        "with_libdrm": False,
        "with_jni": False,
        "with_mediacodec": False,
        "with_xlib": True,
        "with_ffnvcodec": True,
        "with_cuda": False,
        "with_whisper": False,
        "disable_everything": False,
        "disable_all_encoders": False,
        "disable_encoders": None,
        "enable_encoders": None,
        "disable_all_decoders": False,
        "disable_decoders": None,
        "enable_decoders": None,
        "disable_all_hardware_accelerators": False,
        "disable_hardware_accelerators": None,
        "enable_hardware_accelerators": None,
        "disable_all_muxers": False,
        "disable_muxers": None,
        "enable_muxers": None,
        "disable_all_demuxers": False,
        "disable_demuxers": None,
        "enable_demuxers": None,
        "disable_all_parsers": False,
        "disable_parsers": None,
        "enable_parsers": None,
        "disable_all_bitstream_filters": False,
        "disable_bitstream_filters": None,
        "enable_bitstream_filters": None,
        "disable_all_protocols": False,
        "disable_protocols": None,
        "enable_protocols": None,
        "disable_all_devices": False,
        "disable_all_input_devices": False,
        "disable_input_devices": None,
        "enable_input_devices": None,
        "disable_all_output_devices": False,
        "disable_output_devices": None,
        "enable_output_devices": None,
        "disable_all_filters": False,
        "disable_filters": None,
        "enable_filters": None,
    }

    @property
    def _dependencies(self):
        return {
            "avformat": ["avcodec"],
            "avdevice": ["avcodec", "avformat"],
            "avfilter": ["avformat"],
            "with_bzip2": ["avformat"],
            "with_ssl": ["avformat"],
            "with_zlib": ["avcodec"],
            "with_lzma": ["avcodec"],
            "with_libiconv": ["avcodec"],
            "with_libxml2": ["avcodec"],
            "with_libjxl": ["avcodec"],
            "with_openjpeg": ["avcodec"],
            "with_openh264": ["avcodec"],
            "with_vorbis": ["avcodec"],
            "with_opus": ["avcodec"],
            "with_libx264": ["avcodec"],
            "with_libx265": ["avcodec"],
            "with_libvpx": ["avcodec"],
            "with_libmp3lame": ["avcodec"],
            "with_liboapv": ["avcodec"],
            "with_libfdk_aac": ["avcodec"],
            "with_libwebp": ["avcodec"],
            "with_cuda": ["avfilter", "with_ffnvcodec"],
            "with_freetype": ["avfilter"],
            "with_fontconfig": ["avfilter"],
            "with_fribidi": ["avfilter"],
            "with_harfbuzz": ["avfilter"],
            "with_zeromq": ["avfilter", "avformat"],
            "with_libalsa": ["avdevice"],
            "with_xcb": ["avdevice"],
            "with_soxr": ["swresample"],
            "with_pulse": ["avdevice"],
            "with_sndio": ["avdevice"],
            "with_sdl": ["with_programs"],
            "with_libsvtav1": ["avcodec"],
            "with_libaom": ["avcodec"],
            "with_libdav1d": ["avcodec"],
            "with_mediacodec": ["with_jni"],
            "with_xlib": ["avdevice"],
            "with_whisper": ["avfilter"],
        }

    languages = ["C"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            if is_msvc(self) and self.settings.arch == "armv8":
                self.options.with_libsvtav1 = False
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_vaapi
            del self.options.with_vdpau
            del self.options.with_vulkan
            del self.options.with_xcb
            del self.options.with_libalsa
            del self.options.with_pulse
            del self.options.with_xlib
            del self.options.with_libdrm
        if self.settings.os != "Macos":
            del self.options.with_appkit
        if self.settings.os not in ["Macos", "iOS", "tvOS"]:
            del self.options.with_coreimage
            del self.options.with_audiotoolbox
            del self.options.with_videotoolbox
        if not is_apple_os(self):
            del self.options.with_avfoundation
        if not self.settings.os == "Android":
            del self.options.with_jni
            del self.options.with_mediacodec
        if self.settings.os == "Android":
            del self.options.with_libfdk_aac
        if Version(self.version) < "5.1.0":
            self.options.rm_safe("with_libsvtav1")
            self.options.rm_safe("with_libjxl")
        if Version(self.version) < "6.1":
            self.options.rm_safe("with_harfbuzz")
        if Version(self.version) < "8.0":
            self.options.rm_safe("with_liboapv")
            self.options.rm_safe("with_whisper")
        else:
            del self.options.postproc

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_bzip2:
            self.requires("bzip2/[^1.0.8]")
        if self.options.with_lzma:
            self.requires("xz_utils/[^5.4.5]")
        if self.options.with_libiconv:
            self.requires("libiconv/[^1.17]")
        if self.options.get_safe("with_freetype"):
            self.requires("freetype/[^2.13.2]")
        if self.options.with_libxml2:
            self.requires("libxml2/[>=2.12.5 <3]")
        if self.options.get_safe("with_fontconfig"):
            self.requires("fontconfig/[^2.15.0]")
        if self.options.get_safe("with_fribidi"):
            self.requires("fribidi/[^1.0.13]")
        if self.options.get_safe("with_harfbuzz"):
            self.requires("harfbuzz/[*]")
        if self.options.get_safe("with_libjxl"):
            self.requires("libjxl/[<1]")
        if self.options.with_openjpeg:
            self.requires("openjpeg/[^2.5.2]")
        if self.options.with_openh264:
            self.requires("openh264/[^2.4.1]")
        if self.options.with_vorbis:
            self.requires("vorbis/[^1.3.7]")
        if self.options.with_opus:
            self.requires("opus/[^1.4]")
        if self.options.with_zeromq:
            self.requires("zeromq/[^4.3.5]")
        if self.options.with_sdl:
            self.requires("sdl/[^2.30.9]")
        if self.options.with_libx264:
            self.requires("libx264/[*]")
        if self.options.with_libx265:
            self.requires("libx265/[>=3.4 <5]")
        if self.options.with_libvpx:
            self.requires("libvpx/[^1.14.1]")
        if self.options.with_libmp3lame:
            self.requires("libmp3lame/3.100")
        if self.options.get_safe("with_liboapv"):
            self.requires("openapv/[>=0.2.0]")
        if self.options.get_safe("with_libfdk_aac"):
            self.requires("libfdk_aac/2.0.3")
        if self.options.with_libwebp:
            self.requires("libwebp/[^1.3.2]")
        if self.options.with_ssl == "openssl":
            self.requires("openssl/[>=1.1 <4]")
        if self.options.get_safe("with_libalsa"):
            self.requires("libalsa/[^1.2.10]")
        if self.options.get_safe("with_xcb") or self.options.get_safe("with_xlib"):
            self.requires("xorg/system")
        if self.options.get_safe("with_soxr"):
            self.requires("soxr/[>=0.1.3 <1]")
        if self.options.get_safe("with_pulse"):
            self.requires("pulseaudio/[^17.0]")
        if self.options.get_safe("with_sndio"):
            self.requires("libsndio/[^1.9.0]")
        if self.options.get_safe("with_vaapi"):
            self.requires("libva/[^2.21]")
        if self.options.get_safe("with_vdpau"):
            self.requires("libvdpau/[^1.5]")
        if self.options.get_safe("with_vulkan"):
            self.requires("vulkan-loader/[^1.3.277]")
        if self.options.get_safe("with_libsvtav1"):
            self.requires("libsvtav1/[^2.1.0]")
        if self.options.with_libaom:
            self.requires("libaom-av1/[^3.6.1]")
        if self.options.get_safe("with_libdav1d"):
            self.requires("dav1d/[^1.4]")
        if self.options.get_safe("with_libdrm"):
            self.requires("libdrm/[~2.4.119]")
        if self.options.with_cuda:
            self.cuda.requires("npp")
            self.requires(f"ffnvcodec/[^{self.cuda.major}]")
        elif self.options.with_ffnvcodec:
            self.requires("ffnvcodec/[*]")
        if self.options.get_safe("with_whisper"):
            self.requires("whisper-cpp/[^1.7.5]")

    def validate(self):
        if self.options.with_ssl == "securetransport" and not is_apple_os(self):
            raise ConanInvalidConfiguration("securetransport is only available on Apple")

        for dependency, features in self._dependencies.items():
            if not self.options.get_safe(dependency):
                continue
            used = any(self.options.get_safe(f) for f in features)
            if not used:
                raise ConanInvalidConfiguration("FFmpeg '{}' option requires '{}' option to be enabled".format(
                    dependency, "' or '".join(features)))

        if Version(self.version) == "7.0.1" and self.settings.build_type == "Debug":
            # FIXME: FFMpeg fails to build in Debug mode with the following error:
            # ld: libavcodec/libavcodec.a(vvcdsp_init.o): in function `ff_vvc_put_pixels2_8_sse4':
            # src/libavcodec/x86/vvc/vvcdsp_init.c:69: undefined reference to `ff_h2656_put_pixels2_8_sse4'
            # May be related https://github.com/ffvvc/FFmpeg/issues/234
            raise ConanInvalidConfiguration(f"{self.ref} Conan recipe does not support build_type=Debug. Contributions are welcome to fix this issue.")

    def build_requirements(self):
        if self.settings.arch in ("x86", "x86_64"):
            self.tool_requires("nasm/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.1 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
            if self.settings.arch == "armv8" and is_msvc(self):
                self.tool_requires("gas-preprocessor/[*]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    @property
    def _target_arch(self):
        # Taken from acceptable values https://github.com/FFmpeg/FFmpeg/blob/0684e58886881a998f1a7b510d73600ff1df2b90/configure#L5010
        if str(self.settings.arch).startswith("armv8"):
            return "aarch64"
        elif self.settings.arch == "x86":
            return "i686"
        return str(self.settings.arch)

    @property
    def _target_os(self):
        if self.settings.os == "Windows":
            return "mingw32" if self.settings.compiler == "gcc" else "win32"
        elif is_apple_os(self):
            return "darwin"

        # Taken from https://github.com/FFmpeg/FFmpeg/blob/0684e58886881a998f1a7b510d73600ff1df2b90/configure#L5485
        # This is the map of Conan OS settings to FFmpeg acceptable values
        return {
            "AIX": "aix",
            "Android": "android",
            "FreeBSD": "freebsd",
            "Linux": "linux",
            "Neutrino": "qnx",
            "SunOS": "sunos",
        }.get(str(self.settings.os), "none")

    def _patch_sources(self):
        if Version(self.version) < "5.1":
            # suppress MSVC linker warnings: https://trac.ffmpeg.org/ticket/7396
            # warning LNK4049: locally defined symbol x264_levels imported
            # warning LNK4049: locally defined symbol x264_bit_depth imported
            replace_in_file(self, os.path.join(self.source_folder, "libavcodec", "libx264.c"),
                                  "#define X264_API_IMPORTS 1", "")
        if self.options.with_ssl == "openssl" and Version(self.version) < "8.0":
            # https://trac.ffmpeg.org/ticket/5675
            openssl_libs = load(self, os.path.join(self.build_folder, "openssl_libs.list"))
            replace_in_file(self, os.path.join(self.source_folder, "configure"),
                                  "check_lib openssl openssl/ssl.h SSL_library_init -lssl -lcrypto -lws2_32 -lgdi32 ||",
                                  f"check_lib openssl openssl/ssl.h OPENSSL_init_ssl {openssl_libs} || ")

        replace_in_file(self, os.path.join(self.source_folder, "configure"), "echo libx264.lib", "echo x264.lib")

    @property
    def _default_compilers(self):
        if self.settings.compiler == "gcc":
            return {"cc": "gcc", "cxx": "g++"}
        elif self.settings.compiler in ["clang", "apple-clang"]:
            return {"cc": "clang", "cxx": "clang++"}
        elif is_msvc(self):
            return {"cc": "cl.exe", "cxx": "cl.exe"}
        return {}

    def _create_toolchain(self):
        tc = AutotoolsToolchain(self)
        # Custom configure script of ffmpeg understands:
        # --prefix, --bindir, --datadir, --docdir, --incdir, --libdir, --mandir
        # Options --datadir, --docdir, --incdir, and --mandir are not injected by AutotoolsToolchain  but their default value
        # in ffmpeg script matches expected conan install layout.
        # Several options injected by AutotoolsToolchain are unknown from this configure script and must be pruned.
        # This must be done before modifying tc.configure_args, because update_configre_args currently removes
        # duplicate configuration keys, even when they have different values, such as list of encoder flags.
        # See https://github.com/conan-io/conan-center-index/issues/17140 for further information.
        tc.update_configure_args({
            "--sbindir": None,
            "--includedir": None,
            "--oldincludedir": None,
            "--datarootdir": None,
            "--build": None,
            "--host": None,
            "--target": None,
        })
        return tc

    def _get_system_pkg_config_paths(self):
        # Global PKG_CONFIG_PATH is generally not filled by default, so ask for the default paths from pkg-config instead.
        # Assumes that pkg-config is installed system-wide.
        pkg_config = self.conf.get("tools.gnu:pkg_config", default="pkg-config", check_type=str)
        output = io.StringIO()
        try:
            self.run(f"{pkg_config} --variable pc_path pkg-config", output, scope=None)
            return output.getvalue().strip()
        except ConanException:
            return None

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        def opt_enable_disable(what, v):
            return "--{}-{}".format("enable" if v else "disable", what)

        def opt_append_disable_if_set(args, what, v):
            if v:
                args.append(f"--disable-{what}")

        tc = self._create_toolchain()

        args = [
            "--disable-autodetect",
            "--pkg-config-flags=--static",
            "--disable-doc",
            opt_enable_disable("cross-compile", cross_building(self)),
            opt_enable_disable("asm", self.options.with_asm),
            # Libraries
            opt_enable_disable("shared", self.options.shared),
            opt_enable_disable("static", not self.options.shared),
            opt_enable_disable("pic", self.options.get_safe("fPIC", True)),
            # Components
            opt_enable_disable("avdevice", self.options.avdevice),
            opt_enable_disable("avcodec", self.options.avcodec),
            opt_enable_disable("avformat", self.options.avformat),
            opt_enable_disable("swresample", self.options.swresample),
            opt_enable_disable("swscale", self.options.swscale),
            opt_enable_disable("avfilter", self.options.avfilter),

            # Dependencies
            opt_enable_disable("bzlib", self.options.with_bzip2),
            opt_enable_disable("zlib", self.options.with_zlib),
            opt_enable_disable("libxml2", self.options.with_libxml2),
            opt_enable_disable("lzma", self.options.with_lzma),
            opt_enable_disable("iconv", self.options.with_libiconv),
            opt_enable_disable("libfreetype", self.options.get_safe("with_freetype")),
            opt_enable_disable("libfontconfig", self.options.get_safe("with_fontconfig")),
            opt_enable_disable("libfribidi", self.options.get_safe("with_fribidi")),
            opt_enable_disable("libopenjpeg", self.options.with_openjpeg),
            opt_enable_disable("libopenh264", self.options.with_openh264),
            opt_enable_disable("libvorbis", self.options.with_vorbis),
            opt_enable_disable("libopus", self.options.with_opus),
            opt_enable_disable("libzmq", self.options.with_zeromq),
            opt_enable_disable("sdl2", self.options.with_sdl),
            opt_enable_disable("libx264", self.options.with_libx264),
            opt_enable_disable("libx265", self.options.with_libx265),
            opt_enable_disable("libvpx", self.options.with_libvpx),
            opt_enable_disable("libmp3lame", self.options.with_libmp3lame),
            opt_enable_disable("libfdk-aac", self.options.get_safe("with_libfdk_aac")),
            opt_enable_disable("libwebp", self.options.with_libwebp),
            opt_enable_disable("libaom", self.options.with_libaom),
            opt_enable_disable("openssl", self.options.with_ssl == "openssl"),
            opt_enable_disable("alsa", self.options.get_safe("with_libalsa")),
            opt_enable_disable("libpulse", self.options.get_safe("with_pulse")),
            opt_enable_disable("sndio", self.options.get_safe("with_sndio")),
            opt_enable_disable("vaapi", self.options.get_safe("with_vaapi")),
            opt_enable_disable("libdrm", self.options.get_safe("with_libdrm")),
            opt_enable_disable("vdpau", self.options.get_safe("with_vdpau")),
            opt_enable_disable("libxcb", self.options.get_safe("with_xcb")),
            opt_enable_disable("libxcb-shm", self.options.get_safe("with_xcb")),
            opt_enable_disable("libxcb-shape", self.options.get_safe("with_xcb")),
            opt_enable_disable("libxcb-xfixes", self.options.get_safe("with_xcb")),
            opt_enable_disable("libsoxr", self.options.get_safe("with_soxr")),
            opt_enable_disable("appkit", self.options.get_safe("with_appkit")),
            opt_enable_disable("avfoundation", self.options.get_safe("with_avfoundation")),
            opt_enable_disable("coreimage", self.options.get_safe("with_coreimage")),
            opt_enable_disable("audiotoolbox", self.options.get_safe("with_audiotoolbox")),
            opt_enable_disable("videotoolbox", self.options.get_safe("with_videotoolbox")),
            opt_enable_disable("securetransport", self.options.with_ssl == "securetransport"),
            opt_enable_disable("vulkan", self.options.get_safe("with_vulkan")),
            opt_enable_disable("libdav1d", self.options.get_safe("with_libdav1d")),
            opt_enable_disable("jni", self.options.get_safe("with_jni")),
            opt_enable_disable("mediacodec", self.options.get_safe("with_mediacodec")),
            opt_enable_disable("xlib", self.options.get_safe("with_xlib")),
            opt_enable_disable("cuda-nvcc", self.options.with_cuda),
            opt_enable_disable("libnpp", self.options.with_cuda),
            opt_enable_disable("cuvid", self.options.with_cuda),
            opt_enable_disable("ffnvcodec", self.options.with_cuda),
            # Licenses
            opt_enable_disable("nonfree", self.options.get_safe("with_libfdk_aac") or self.options.with_cuda or
                               (self.options.with_ssl and (self.options.with_libx264 or self.options.with_libx265 or self.options.get_safe("postproc")))),
            opt_enable_disable("gpl", self.options.with_libx264 or self.options.with_libx265)
        ]

        # Individual Component Options
        opt_append_disable_if_set(args, "everything", self.options.disable_everything)
        opt_append_disable_if_set(args, "encoders", self.options.disable_all_encoders)
        opt_append_disable_if_set(args, "decoders", self.options.disable_all_decoders)
        opt_append_disable_if_set(args, "hwaccels", self.options.disable_all_hardware_accelerators)
        opt_append_disable_if_set(args, "muxers", self.options.disable_all_muxers)
        opt_append_disable_if_set(args, "demuxers", self.options.disable_all_demuxers)
        opt_append_disable_if_set(args, "parsers", self.options.disable_all_parsers)
        opt_append_disable_if_set(args, "bsfs", self.options.disable_all_bitstream_filters)
        opt_append_disable_if_set(args, "protocols", self.options.disable_all_protocols)
        opt_append_disable_if_set(args, "devices", self.options.disable_all_devices)
        opt_append_disable_if_set(args, "indevs", self.options.disable_all_input_devices)
        opt_append_disable_if_set(args, "outdevs", self.options.disable_all_output_devices)
        opt_append_disable_if_set(args, "filters", self.options.disable_all_filters)

        def _split_and_format_options_string(flag_name, options_list):
            return [f"--{flag_name}={item}" for item in str(options_list).replace(",", " ").split() if item]

        args += _split_and_format_options_string("enable-encoder", self.options.enable_encoders)
        args += _split_and_format_options_string("disable-encoder", self.options.disable_encoders)
        args += _split_and_format_options_string("enable-decoder", self.options.enable_decoders)
        args += _split_and_format_options_string("disable-decoder", self.options.disable_decoders)
        args += _split_and_format_options_string("enable-hwaccel", self.options.enable_hardware_accelerators)
        args += _split_and_format_options_string("disable-hwaccel", self.options.disable_hardware_accelerators)
        args += _split_and_format_options_string("enable-muxer", self.options.enable_muxers)
        args += _split_and_format_options_string("disable-muxer", self.options.disable_muxers)
        args += _split_and_format_options_string("enable-demuxer", self.options.enable_demuxers)
        args += _split_and_format_options_string("disable-demuxer", self.options.disable_demuxers)
        args += _split_and_format_options_string("enable-parser", self.options.enable_parsers)
        args += _split_and_format_options_string("disable-parser", self.options.disable_parsers)
        args += _split_and_format_options_string("enable-bsf", self.options.enable_bitstream_filters)
        args += _split_and_format_options_string("disable-bsf", self.options.disable_bitstream_filters)
        args += _split_and_format_options_string("enable-protocol", self.options.enable_protocols)
        args += _split_and_format_options_string("disable-protocol", self.options.disable_protocols)
        args += _split_and_format_options_string("enable-indev", self.options.enable_input_devices)
        args += _split_and_format_options_string("disable-indev", self.options.disable_input_devices)
        args += _split_and_format_options_string("enable-outdev", self.options.enable_output_devices)
        args += _split_and_format_options_string("disable-outdev", self.options.disable_output_devices)
        args += _split_and_format_options_string("enable-filter", self.options.enable_filters)
        args += _split_and_format_options_string("disable-filter", self.options.disable_filters)

        if Version(self.version) < "8.0":
            args.append(opt_enable_disable("postproc", self.options.postproc))
        if "with_libsvtav1" in self.options:
            args.append(opt_enable_disable("libsvtav1", self.options.with_libsvtav1))
        if "with_libjxl" in self.options:
            args.append(opt_enable_disable("libjxl", self.options.with_libjxl))
        if "with_harfbuzz" in self.options:
            args.append(opt_enable_disable("libharfbuzz", self.options.with_harfbuzz))
        if "with_liboapv" in self.options:
            args.append(opt_enable_disable("liboapv", self.options.with_liboapv))
        if "with_whisper" in self.options:
            args.append(opt_enable_disable("whisper", self.options.with_whisper))

        if is_apple_os(self):
            # relocatable shared libs
            args.append("--install-name-dir=@rpath")
        args.append(f"--arch={self._target_arch}")
        if self.settings.build_type == "Debug":
            args.extend([
                "--disable-optimizations",
                "--disable-mmx",
                "--disable-stripping",
                "--enable-debug",
            ])
        if not self.options.with_programs:
            args.append("--disable-programs")
        # since ffmpeg"s build system ignores CC and CXX
        compilers_from_conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        buildenv_vars = VirtualBuildEnv(self).vars()
        nm = compilers_from_conf.get("nm", buildenv_vars.get("NM"))
        if nm:
            args.append(f"--nm={unix_path(self, nm)}")
        ar = compilers_from_conf.get("ar", buildenv_vars.get("AR"))
        if ar:
            args.append(f"--ar={unix_path(self, ar)}")
        if self.options.with_asm:
            asm = compilers_from_conf.get("asm", buildenv_vars.get("AS"))
            if asm:
                args.append(f"--as={unix_path(self, asm)}")
        strip = compilers_from_conf.get("strip", buildenv_vars.get("STRIP"))
        if strip:
            args.append(f"--strip={unix_path(self, strip)}")
        cc = compilers_from_conf.get("c", buildenv_vars.get("CC", self._default_compilers.get("cc")))
        if cc:
            args.append(f"--cc={unix_path(self, cc)}")
        cxx = compilers_from_conf.get("cpp", buildenv_vars.get("CXX", self._default_compilers.get("cxx")))
        if cxx:
            args.append(f"--cxx={unix_path(self, cxx)}")
        ld = buildenv_vars.get("LD")
        if ld:
            args.append(f"--ld={unix_path(self, ld)}")
        ranlib = compilers_from_conf.get("ranlib", buildenv_vars.get("RANLIB"))
        if ranlib:
            args.append(f"--ranlib={unix_path(self, ranlib)}")
        if cross_building(self):
            build_cc = AutotoolsToolchain(self).vars()["CC_FOR_BUILD"]
            args.append(f"--host-cc={unix_path(self, build_cc)}")
        if self.options.with_cuda:
            args.append("--nvcc=nvcc")
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=buildenv_vars.get("PKG_CONFIG", "pkgconf"), check_type=str)
        if pkg_config:
            args.append(f"--pkg-config={unix_path(self, pkg_config)}")
        if is_msvc(self):
            args.append("--toolchain=msvc")
            if not check_min_vs(self, "190", raise_invalid=False):
                # Visual Studio 2013 (and earlier) doesn't support "inline" keyword for C (only for C++)
                tc.extra_defines.append("inline=__inline")
        if self.settings.compiler == "apple-clang" and Version(self.settings.compiler.version) >= "15":
            # Workaround for link error "ld: building exports trie: duplicate symbol '_av_ac3_parse_header'"
            tc.extra_ldflags.append("-Wl,-ld_classic")
        if cross_building(self):
            args.append(f"--target-os={self._target_os}")
            if is_apple_os(self) and self.options.with_audiotoolbox:
                args.append("--disable-outdev=audiotoolbox")

        if tc.cflags:
            args.append("--extra-cflags={}".format(" ".join(tc.cflags)))
        if tc.ldflags:
            args.append("--extra-ldflags={}".format(" ".join(tc.ldflags)))
        tc.configure_args.extend(args)
        env = tc.environment()
        tc.generate(env)

        if is_msvc(self):
            # Custom AutotoolsDeps for cl like compilers
            # workaround for https://github.com/conan-io/conan/issues/12784
            cpp_info = CppInfo(self)
            for dependency in reversed(self.dependencies.host.topological_sort.values()):
                cpp_info.merge(dependency.cpp_info.aggregated_components())
            env = Environment()
            env.append("CPPFLAGS", [f"-I{unix_path(self, p)}" for p in cpp_info.includedirs] + [f"-D{d}" for d in cpp_info.defines])
            env.append("_LINK_", [lib if lib.endswith(".lib") else f"{lib}.lib" for lib in cpp_info.libs])
            env.append("LDFLAGS", [f"-L{unix_path(self, p)}" for p in cpp_info.libdirs] + cpp_info.sharedlinkflags + cpp_info.exelinkflags)
            env.append("CXXFLAGS", cpp_info.cxxflags)
            env.append("CFLAGS", cpp_info.cflags)
            env.vars(self).save_script("conanautotoolsdeps_cl_workaround")
        else:
            deps = AutotoolsDeps(self)
            deps.generate()

        using_system_deps = any(dep.ref.version == "system" for dep, _ in self.dependencies.items())
        if using_system_deps:
            system_pkg_config_path = self._get_system_pkg_config_paths()
            if system_pkg_config_path:
                env = Environment()
                env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
                env.append_path("PKG_CONFIG_PATH", system_pkg_config_path)
                env.vars(self).save_script("system_pkg_config_path")

        deps = PkgConfigDeps(self)
        deps.generate()

        if self.options.with_ssl == "openssl":
            openssl_libs = " ".join(f"-l{lib}" for lib in self.dependencies["openssl"].cpp_info.aggregated_components().libs)
            save(self, os.path.join(self.build_folder, "openssl_libs.list"), openssl_libs)

        if self.options.with_cuda:
            # FFMpeg embeds a handwritten .ptx as a C array and JIT-s it at runtime
            # instead of building for specific architectures.
            cuda_tc = self.cuda.CudaToolchain(skip_arch_flags=True)
            cuda_tc.generate()

    def build(self):
        self._patch_sources()
        if self.options.with_libx264:
            # ffmepg expects libx264.pc instead of x264.pc
            with chdir(self, self.generators_folder):
                shutil.copy("x264.pc", "libx264.pc")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _fix_library_names(self, path):
        if is_msvc(self) or self.settings.os == "Windows" and self.settings.get_safe("compiler.runtime"):
            for filename_old in Path(path).glob("*.a"):
                filename_new = filename_old.name[3:-2] + ".lib"
                rename(self, filename_old, filename_old.parent / filename_new)

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        if is_msvc(self):
            if self.options.shared:
                # ffmpeg created `.lib` files in the `/bin` folder
                for path in Path(self.package_folder, "bin").glob("*.lib"):
                    rename(self, path, os.path.join(self.package_folder, "lib", path.name))
                rm(self, "*.def", os.path.join(self.package_folder, "lib"))
            else:
                # ffmpeg produces `.a` files that are actually `.lib` files
                self._fix_library_names(os.path.join(self.package_folder, "lib"))

    def _get_component_version(self, component):
        includedir = Path(self.package_folder, "include", f"lib{component}")
        version_headers = [includedir / "version.h", includedir / "version_major.h"]
        content = "".join(load(self, header) for header in version_headers if header.exists())
        return ".".join(re.search(rf"VERSION_{x}[ \t]+(\d+)", content)[1] for x in ["MAJOR", "MINOR", "MICRO"])

    def package_info(self):
        if self.options.with_programs:
            if self.options.with_sdl:
                self.cpp_info.components["programs"].requires = ["sdl::libsdl2"]

        def _add_component(name, dependencies):
            component = self.cpp_info.components[name]
            component.set_property("pkg_config_name", f"lib{name}")
            component.set_property("component_version", self._get_component_version(name))
            component.libs = [name]
            if name != "avutil":
                component.requires = ["avutil"]
            for dep in dependencies:
                if self.options.get_safe(dep):
                    component.requires.append(dep)
            if self.settings.os in ("FreeBSD", "Linux"):
                component.system_libs.append("m")
            return component

        avutil = _add_component("avutil", [])
        if self.options.avdevice:
            avdevice = _add_component("avdevice", ["avfilter", "swscale", "avformat", "avcodec", "swresample", "postproc"])
        if self.options.avfilter:
            avfilter = _add_component("avfilter", ["swscale", "avformat", "avcodec", "swresample", "postproc"])
        if self.options.avformat:
            avformat = _add_component("avformat", ["avcodec", "swscale"])
        if self.options.avcodec:
            avcodec = _add_component("avcodec", ["swresample"])
        if self.options.swscale:
            _add_component("swscale", [])
        if self.options.swresample:
            swresample = _add_component("swresample", [])
            if self.options.get_safe("with_soxr"):
                swresample.requires.append("soxr::soxr")
        if self.options.get_safe("postproc"):
            _add_component("postproc", [])

        if self.settings.os in ("FreeBSD", "Linux"):
            avutil.system_libs.extend(["pthread", "dl"])
            if self.options.get_safe("fPIC"):
                if self.settings.compiler in ("gcc", "clang"):
                    # https://trac.ffmpeg.org/ticket/1713
                    # https://ffmpeg.org/platform.html#Advanced-linking-configuration
                    # https://ffmpeg.org/pipermail/libav-user/2014-December/007719.html
                    avcodec.exelinkflags.append("-Wl,-Bsymbolic")
                    avcodec.sharedlinkflags.append("-Wl,-Bsymbolic")
            if self.options.avfilter:
                avfilter.system_libs.append("pthread")
        elif self.settings.os == "Windows":
            if self.options.avcodec:
                avcodec.system_libs = ["mfplat", "mfuuid", "strmiids"]
            if self.options.avdevice:
                avdevice.system_libs = ["ole32", "psapi", "strmiids", "uuid", "oleaut32", "shlwapi", "gdi32", "vfw32"]
            avutil.system_libs = ["user32", "bcrypt"]
            avformat.system_libs = ["secur32"]
            if Version(self.version) >= "8.0":
                avformat.system_libs.extend(["ncrypt", "crypt32"])
        elif is_apple_os(self):
            if self.options.avdevice:
                avdevice.frameworks = ["CoreFoundation", "Foundation", "CoreGraphics"]
            if self.options.avfilter:
                avfilter.frameworks = ["CoreGraphics"]
            if self.options.avcodec:
                avcodec.frameworks = ["CoreFoundation", "CoreVideo", "CoreMedia"]
            if self.settings.os == "Macos":
                if self.options.avdevice:
                    avdevice.frameworks.append("OpenGL")
                if self.options.avfilter:
                    avfilter.frameworks.append("OpenGL")

        if self.options.avdevice:
            if self.options.get_safe("with_libalsa"):
                avdevice.requires.append("libalsa::libalsa")
            if self.options.get_safe("with_xcb"):
                avdevice.requires.extend(["xorg::xcb", "xorg::xcb-shm", "xorg::xcb-xfixes", "xorg::xcb-shape", "xorg::xv", "xorg::xext"])
            if self.options.get_safe("with_xlib"):
                avdevice.requires.extend(["xorg::x11", "xorg::xext", "xorg::xv"])
            if self.options.get_safe("with_pulse"):
                avdevice.requires.append("pulseaudio::pulseaudio")
            if self.options.get_safe("with_sndio"):
                avdevice.requires.append("libsndio::libsndio")
            if self.options.get_safe("with_appkit"):
                avdevice.frameworks.append("AppKit")
            if self.options.get_safe("with_avfoundation"):
                avdevice.frameworks.append("AVFoundation")
            if self.options.get_safe("with_audiotoolbox"):
                avdevice.frameworks.append("CoreAudio")
            if self.settings.os == "Android" and not self.options.shared:
                avdevice.system_libs.extend(["android", "camera2ndk", "mediandk"])

        if self.options.avcodec:
            if self.options.with_zlib:
                avcodec.requires.append("zlib-ng::zlib-ng")
            if self.options.with_lzma:
                avcodec.requires.append("xz_utils::xz_utils")
            if self.options.with_libiconv:
                avcodec.requires.append("libiconv::libiconv")
            if self.options.with_libxml2:
                avcodec.requires.append("libxml2::libxml2")
            if self.options.with_openjpeg:
                avcodec.requires.append("openjpeg::openjpeg")
            if self.options.with_openh264:
                avcodec.requires.append("openh264::openh264")
            if self.options.with_vorbis:
                avcodec.requires.append("vorbis::vorbis")
            if self.options.with_opus:
                avcodec.requires.append("opus::opus")
            if self.options.with_libx264:
                avcodec.requires.append("libx264::libx264")
            if self.options.with_libx265:
                avcodec.requires.append("libx265::libx265")
            if self.options.with_libvpx:
                avcodec.requires.append("libvpx::libvpx")
            if self.options.with_libmp3lame:
                avcodec.requires.append("libmp3lame::libmp3lame")
            if self.options.get_safe("with_liboapv"):
                avcodec.requires.append("openapv::openapv")
            if self.options.get_safe("with_libfdk_aac"):
                avcodec.requires.append("libfdk_aac::libfdk_aac")
            if self.options.with_libwebp:
                avcodec.requires.append("libwebp::libwebp")
            if self.options.get_safe("with_audiotoolbox"):
                avcodec.frameworks.append("AudioToolbox")
            if self.options.get_safe("with_videotoolbox"):
                avcodec.frameworks.append("VideoToolbox")
            if self.options.get_safe("with_libsvtav1"):
                avcodec.requires.append("libsvtav1::libsvtav1")
            if self.options.get_safe("with_libaom"):
                avcodec.requires.append("libaom-av1::libaom-av1")
            if self.options.get_safe("with_libdav1d"):
                avcodec.requires.append("dav1d::dav1d")
            if self.options.with_ffnvcodec:
                avcodec.requires.append("ffnvcodec::ffnvcodec")
            if self.options.get_safe("with_libjxl"):
                avcodec.requires.append("libjxl::libjxl")

        if self.options.avformat:
            if self.options.with_bzip2:
                avformat.requires.append("bzip2::bzip2")
            if self.options.with_zeromq:
                avformat.requires.append("zeromq::libzmq")
            if self.options.with_ssl == "openssl":
                avformat.requires.append("openssl::ssl")
            elif self.options.with_ssl == "securetransport":
                avformat.frameworks.append("Security")

        if self.options.avfilter:
            if self.options.with_cuda:
                avfilter.requires.append("ffnvcodec::ffnvcodec")
                avfilter.requires.append("npp::nppi")
            if self.options.get_safe("with_freetype"):
                avfilter.requires.append("freetype::freetype")
            if self.options.get_safe("with_fontconfig"):
                avfilter.requires.append("fontconfig::fontconfig")
            if self.options.get_safe("with_fribidi"):
                avfilter.requires.append("fribidi::fribidi")
            if self.options.get_safe("with_harfbuzz"):
                avfilter.requires.append("harfbuzz::harfbuzz")
            if self.options.with_zeromq:
                avfilter.requires.append("zeromq::libzmq")
            if self.options.get_safe("with_appkit"):
                avfilter.frameworks.append("AppKit")
            if self.options.get_safe("with_coreimage"):
                avfilter.frameworks.append("CoreImage")
            if Version(self.version) >= "5.0" and is_apple_os(self):
                avfilter.frameworks.append("Metal")
            if self.options.get_safe("with_whisper"):
                avfilter.requires.append("whisper-cpp::whisper-cpp")

        if self.options.get_safe("with_libdrm"):
            avutil.requires.append("libdrm::libdrm_libdrm")
        if self.options.get_safe("with_vaapi"):
            avutil.requires.append("libva::libva")
        if self.options.get_safe("with_xcb"):
            avutil.requires.append("xorg::x11")
        if self.options.get_safe("with_vdpau"):
            avutil.requires.append("libvdpau::libvdpau")
        if self.options.with_ssl == "openssl":
            avutil.requires.append("openssl::ssl")
        if self.options.get_safe("with_vulkan"):
            avutil.requires.append("vulkan-loader::vulkan-loader")
            if Version(self.version) >= "8.0":
                avfilter.requires.append("vulkan-loader::vulkan-loader")
