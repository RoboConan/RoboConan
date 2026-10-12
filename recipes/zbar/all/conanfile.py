import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class ZbarConan(ConanFile):
    name = "zbar"
    description = ("ZBar is an open source software suite for reading bar codes "
                   "from various sources, such as video streams, image files and raw intensity sensors")
    license = "LGPL-2.1-only"
    homepage = "http://zbar.sourceforge.net/"
    topics = ("barcode", "scanner", "decoder", "reader", "bar")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "with_video": [True, False],
        "with_imagemagick": [True, False],
        "with_gtk": [True, False],
        "with_qt": [True, False],
        "with_python_bindings": [True, False],
        "with_x": [True, False],
        "with_xshm": [True, False],
        "with_xv": [True, False],
        "with_jpeg": [True, False],
        "enable_pthread": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "with_video": False,
        "with_imagemagick": False,
        "with_gtk": False,
        "with_qt": False,
        "with_python_bindings": False,
        "with_x": False,
        "with_xshm": False,
        "with_xv": False,
        "with_jpeg": False,
        "enable_pthread": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libiconv/[^1.17]")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.with_imagemagick:
            self.requires("imagemagick/7.0.11-14")
        if self.options.with_gtk:
            # GTK 4 is not yet supported
            self.requires("gtk/[^3.24]")
        if self.options.with_qt:
            self.requires("qt/[>=5.15 <7]")
        if self.options.with_xv or self.options.with_xshm or self.options.with_x:
            self.requires("xorg/system")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("Zbar can't be built on Windows")
        if is_apple_os(self) and not self.options.shared:
            raise ConanInvalidConfiguration("Zbar can't be built static on macOS")

    def build_requirements(self):
        self.tool_requires("gnu-config/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if Version(self.version) >= "0.22":
            self.tool_requires("libtool/[^2.4.7]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        yes_no = lambda v: "yes" if v else "no"
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--enable-video={yes_no(self.options.with_video)}",
            f"--with-imagemagick={yes_no(self.options.with_imagemagick)}",
            f"--with-gtk={yes_no(self.options.with_gtk)}",
            f"--with-qt={yes_no(self.options.with_qt)}",
            f"--with-python={yes_no(self.options.with_python_bindings)}",
            f"--with-x={yes_no(self.options.with_x)}",
            f"--with-xshm={yes_no(self.options.with_xshm)}",
            f"--with-xv={yes_no(self.options.with_xv)}",
            f"--with-jpeg={yes_no(self.options.with_jpeg)}",
            f"--enable-pthread={yes_no(self.options.enable_pthread)}",
            f"USE_NLS={yes_no(self.options.i18n)}",
        ])
        env = tc.environment()
        compilers_from_conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        buildenv_vars = VirtualBuildEnv(self).vars()
        nm = compilers_from_conf.get("nm", buildenv_vars.get("NM", "nm"))
        env.define_path("NM", nm)
        tc.generate(env)

        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        for gnu_config in [
            self.conf.get("user.gnu-config:config_guess", check_type=str),
            self.conf.get("user.gnu-config:config_sub", check_type=str),
        ]:
            if gnu_config:
                copy(self, os.path.basename(gnu_config),
                           src=os.path.dirname(gnu_config),
                           dst=os.path.join(self.source_folder, "config"))

        if not self.options.i18n and Version(self.version) >= "0.22":
            configure_ac = os.path.join(self.source_folder, "configure.ac")
            replace_in_file(self, configure_ac, "AM_GNU_GETTEXT", "# AM_GNU_GETTEXT")
            replace_in_file(self, configure_ac, "po/Makefile.in", "")

        autotools = Autotools(self)
        if Version(self.version) >= "0.22":
            autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "zbar"))  # JNI bindings
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "zbar")
        self.cpp_info.libs = ["zbar"]
        if self.options.i18n:
            self.cpp_info.resdirs = ["share"]
        if self.settings.os in ("FreeBSD", "Linux") and self.options.enable_pthread:
            self.cpp_info.system_libs = ["pthread"]

        self.cpp_info.requires.append("libiconv::libiconv")
        if self.options.with_jpeg:
            self.cpp_info.requires.append("libjpeg-meta::jpeg")
        if self.options.with_imagemagick:
            self.cpp_info.requires.append("imagemagick::MagickWand")
        if self.options.with_gtk:
            self.cpp_info.requires.append("gtk::gtk+-3.0")
        if self.options.with_qt:
            self.cpp_info.requires.extend(["qt::qtGui", "qt::qtWidgets"])
            if self.dependencies["qt"].ref.version.major == 5:
                self.cpp_info.requires.append("qt::qtX11Extras")
        if self.options.with_xv:
            self.cpp_info.requires.append("xorg::xv")
        if self.options.with_x or self.options.with_xshm:
            self.cpp_info.requires.append("xorg::x11")
