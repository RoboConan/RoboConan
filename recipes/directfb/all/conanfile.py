import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building, stdcpp_library
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class DirectfbConan(ConanFile):
    name = "directfb"
    description = "DirectFB is a graphics library which was designed with embedded systems in mind."
    license = "LGPL-2.1-or-later"
    homepage = "https://directfb1.org/"
    topics = ("framebuffer", "graphics", "embedded")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "build_divine": [True, False],
        "build_fusiondale": [True, False],
        "build_fusionsound": [True, False],
        "build_sawman": [True, False],
        # graphics
        "with_drm": [True, False],
        "with_egl": [True, False],
        "with_ffmpeg": [True, False],
        "with_freetype": [True, False],
        "with_gif": [True, False],
        "with_gstreamer": [True, False],
        "with_imlib2": [True, False],
        "with_jasper": [True, False],
        "with_jpeg": [True, False],
        "with_linotype": [True, False],
        "with_mesa": [True, False],
        "with_mng": [True, False],
        "with_png": [True, False],
        "with_sdl": [True, False],
        "with_tiff": [True, False],
        "with_v4l2": [True, False],
        "with_vdpau": [True, False],
        "with_wayland": [True, False],
        "with_webp": [True, False],
        "with_x11": [True, False],
        # audio
        "with_alsa": [True, False],
        "with_mad": [True, False],
        "with_vorbis": [True, False],
    }
    default_options = {
        "build_divine": False,
        "build_fusiondale": False,
        "build_fusionsound": False,
        "build_sawman": False,
        # graphics
        "with_drm": True,
        "with_egl": True,
        "with_ffmpeg": False,
        "with_freetype": True,
        "with_gif": True,
        "with_gstreamer": False,
        "with_imlib2": False,
        "with_jasper": False,
        "with_jpeg": True,
        "with_linotype": False,
        "with_mesa": True,
        "with_mng": False,
        "with_png": True,
        "with_sdl": False,
        "with_tiff": False,
        "with_v4l2": False,
        "with_vdpau": False,
        "with_wayland": True,
        "with_webp": True,
        "with_x11": True,
        # audio
        "with_alsa": True,
        "with_mad": True,
        "with_vorbis": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if not self.options.build_fusionsound:
            del self.options.with_alsa
            del self.options.with_mad
            del self.options.with_vorbis
        if not self.options.with_x11:
            del self.options.with_vdpau

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        if self.options.with_egl:
            self.requires("egl/system")
        if self.options.with_sdl:
            self.requires("sdl/[^2.32.2]")
        if self.options.with_mesa:
            self.requires("opengl/system")
        if self.options.with_drm:
            self.requires("libdrm/[~2.4.124]")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.with_png:
            self.requires("libpng/[~1.6]")
        if self.options.with_mng:
            self.requires("libmng/[^2.0.3]")
        if self.options.with_gstreamer:
            self.requires("gst-plugins-base/[^1.24]")
        if self.options.with_gif:
            self.requires("giflib/[>=5.2 <7]")
        if self.options.with_tiff:
            self.requires("libtiff/[>=4.5 <5]")
        if self.options.with_imlib2:
            self.requires("imlib2/[^1.12]")
        if self.options.with_jasper:
            self.requires("jasper/[^4.2]")
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/[>=4]")
        if self.options.with_freetype:
            self.requires("freetype/[^2.13.2]")
        if self.options.with_v4l2:
            self.requires("libv4l/1.28.1")
        if self.options.with_webp:
            self.requires("libwebp/[^1.3.2]")
        if self.options.with_wayland:
            self.requires("wayland/[^1.22.0]")
        if self.options.with_x11:
            self.requires("xorg/system")
            if self.options.with_vdpau:
                self.requires("libvdpau/[^1.5]")
        if self.options.get_safe("with_alsa"):
            self.requires("libalsa/[^1.2.13]")
        if self.options.get_safe("with_vorbis"):
            self.requires("vorbis/[^1.3.7]")
        if self.options.get_safe("with_mad"):
            self.requires("libmad/0.15.1b")
        # self.requires("tremor/1.2.1")
        # self.requires("libtimidity/0.2.7")
        # self.requires("libcddb/1.3.2")

    def validate(self):
        if self.settings.os == "Windows":
            # Not tested on Windows
            raise ConanInvalidConfiguration("Windows is not supported.")

    def build_requirements(self):
        self.tool_requires("libtool/[^2.4.7]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if is_msvc(self):
            self.tool_requires("automake/[^1.18.1]")
        self.tool_requires("wayland/1.23.0")

    def source(self):
        sources_info = self.conan_data["sources"][self.version]
        get(self, **sources_info["directfb"], strip_root=True)
        get(self, **sources_info["flux"], strip_root=True, destination="flux")
        apply_conandata_patches(self)

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")

        def opt_enable(what, v):
            return "--{}-{}".format("enable" if v else "disable", what)

        tc = AutotoolsToolchain(self, namespace="flux")
        tc.make_args.append(f"CC={tc.vars().get('CC_FOR_BUILD', 'cc')}")
        tc.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            opt_enable("debug", self.settings.build_type == "Debug"),
            opt_enable("divine", self.options.build_divine),
            opt_enable("fusiondale", self.options.build_fusiondale),
            opt_enable("fusionsound", self.options.build_fusionsound),
            opt_enable("sawman", self.options.build_sawman),
            opt_enable("wayland", self.options.with_wayland),
            opt_enable("x11", self.options.with_x11),
            opt_enable("x11vdpau", self.options.get_safe("with_vdpau")),
            opt_enable("alsa", self.options.get_safe("with_alsa")),
            opt_enable("cdda", False),
            opt_enable("mad", self.options.get_safe("with_mad")),
            opt_enable("timidity", False),
            opt_enable("tremor", False),
            opt_enable("vorbis", self.options.get_safe("with_vorbis")),
            opt_enable("drmkms", self.options.with_drm),
            opt_enable("egl", self.options.with_egl),
            opt_enable("ffmpeg", self.options.with_ffmpeg),
            opt_enable("freetype", self.options.with_freetype),
            opt_enable("gif", self.options.with_gif),
            opt_enable("gstreamer", self.options.with_gstreamer),
            opt_enable("imlib2", self.options.with_imlib2),
            opt_enable("jpeg", self.options.with_jpeg),
            opt_enable("jpeg2000", self.options.with_jasper),
            opt_enable("linotype", False),
            opt_enable("mesa", self.options.with_mesa),
            opt_enable("mng", self.options.with_mng),
            opt_enable("openquicktime", False),
            opt_enable("png", self.options.with_png),
            opt_enable("pvr2d", False),
            opt_enable("sdl", self.options.with_sdl),
            opt_enable("tiff", self.options.with_tiff),
            opt_enable("video4linux", False),
            opt_enable("video4linux2", self.options.with_v4l2),
            opt_enable("webp", self.options.with_webp),
            opt_enable("zlib", True),
        ])
        # Drop register keywords for C++17 and later
        tc.extra_defines.append("register=")
        env = tc.environment()
        env.append_path("PATH", os.path.join(self.source_folder, "flux", "src"))
        tc.generate(env)

        tc = PkgConfigDeps(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        with chdir(self, os.path.join(self.source_folder, "flux")):
            autotools = Autotools(self, namespace="flux")
            autotools.autoreconf(build_script_folder="flux")
            autotools.configure(build_script_folder="flux")
            autotools.make()

        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        fix_apple_shared_install_name(self)
        replace_in_file(self, os.path.join(self.package_folder, "bin", "directfb-config"),
                        "prefix=/",
                        "prefix=`dirname $0`/..")

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "directfb_do_not_use")
        self.cpp_info.libs = ["directfb"]
        self.cpp_info.resdirs = ["share"]

        v = Version(self.version)
        pkgconfig_extra = f"moduledir=${{prefix}}/lib/directfb-{v.major}.{v.minor}-{v.patch}"

        self.cpp_info.components["direct"].set_property("pkg_config_name", "direct")
        self.cpp_info.components["direct"].set_property("pkg_config_custom_content", pkgconfig_extra)
        self.cpp_info.components["direct"].libs = ["direct"]
        self.cpp_info.components["direct"].includedirs = ["include", os.path.join("include", "directfb")]
        self.cpp_info.components["direct"].resdirs = ["share"]
        self.cpp_info.components["direct"].defines = ["_REENTRANT"]
        libcxx = stdcpp_library(self)
        if libcxx:
            self.cpp_info.components["direct"].system_libs.append(libcxx)

        self.cpp_info.components["fusion"].set_property("pkg_config_name", "fusion")
        self.cpp_info.components["fusion"].set_property("pkg_config_custom_content", pkgconfig_extra)
        self.cpp_info.components["fusion"].libs = ["fusion"]
        self.cpp_info.components["fusion"].includedirs = [os.path.join("include", "directfb")]
        self.cpp_info.components["fusion"].requires = ["direct"]

        self.cpp_info.components["directfb_"].set_property("pkg_config_name", "directfb")
        self.cpp_info.components["directfb_"].set_property("pkg_config_custom_content", pkgconfig_extra)
        self.cpp_info.components["directfb_"].libs = ["directfb"]
        self.cpp_info.components["directfb_"].includedirs = [os.path.join("include", "directfb")]
        self.cpp_info.components["directfb_"].requires = ["fusion", "direct", "zlib-ng::zlib-ng"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["directfb_"].system_libs.extend(["dl", "m", "pthread"])

        self.cpp_info.components["++dfb"].set_property("pkg_config_name", "++dfb")
        self.cpp_info.components["++dfb"].set_property("pkg_config_custom_content", pkgconfig_extra)
        self.cpp_info.components["++dfb"].libs = ["++dfb"]
        self.cpp_info.components["++dfb"].includedirs = [os.path.join("include", "++dfb")]
        self.cpp_info.components["++dfb"].requires = ["directfb_"]

        if self.options.build_divine:
            self.cpp_info.components["divine"].set_property("pkg_config_name", "divine")
            self.cpp_info.components["divine"].set_property("pkg_config_custom_content", pkgconfig_extra)
            self.cpp_info.components["divine"].libs = ["divine"]
            self.cpp_info.components["divine"].includedirs = [os.path.join("include", "divine")]
            self.cpp_info.components["divine"].requires = ["directfb_"]

        if self.options.build_fusiondale:
            self.cpp_info.components["fusiondale"].set_property("pkg_config_name", "fusiondale")
            self.cpp_info.components["fusiondale"].set_property("pkg_config_custom_content", pkgconfig_extra)
            self.cpp_info.components["fusiondale"].libs = ["fusiondale"]
            self.cpp_info.components["fusiondale"].includedirs = [os.path.join("include", "fusiondale")]
            self.cpp_info.components["fusiondale"].requires = ["fusion"]

        if self.options.build_fusionsound:
            self.cpp_info.components["fusionsound"].set_property("pkg_config_name", "fusionsound")
            self.cpp_info.components["fusionsound"].set_property("pkg_config_custom_content", pkgconfig_extra)
            self.cpp_info.components["fusionsound"].libs = ["fusionsound"]
            self.cpp_info.components["fusionsound"].includedirs = [os.path.join("include", "fusionsound")]
            self.cpp_info.components["fusionsound"].requires = ["fusion"]

        if self.options.build_sawman:
            self.cpp_info.components["sawman"].set_property("pkg_config_name", "sawman")
            self.cpp_info.components["sawman"].set_property("pkg_config_custom_content", pkgconfig_extra)
            self.cpp_info.components["sawman"].libs = ["sawman"]
            self.cpp_info.components["sawman"].includedirs = [os.path.join("include", "sawman")]
            self.cpp_info.components["sawman"].requires = ["directfb_"]

        self.cpp_info.components["_plugins"].requires = [
            f"{req.ref.name}::{req.ref.name}" for req, _ in self.dependencies.direct_host.items()
        ]
