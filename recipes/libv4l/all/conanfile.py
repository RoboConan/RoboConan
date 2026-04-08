import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class Libv4lConan(ConanFile):
    name = "libv4l"
    description = "libv4l is a collection of libraries which adds a thin abstraction layer on top of video4linux2 devices."
    license = "LGPL-2.1-or-later"
    homepage = "https://linuxtv.org/wiki/index.php/V4l-utils"
    topics = ("video4linux2", "v4l", "video", "camera", "webcam")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "build_plugins": [True, False],
        "build_wrappers": [True, False],
        "build_libdvbv5": [True, False],
        "with_jpeg": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "build_plugins": True,
        "build_wrappers": True,
        "build_libdvbv5": False,
        "with_jpeg": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def configure(self):
        if not self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.build_libdvbv5:
            del self.options.i18n

    def requirements(self):
        if self.options.build_libdvbv5:
            self.requires("libudev/[>=255 <system]")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("libv4l is only supported on Linux")
        check_min_cppstd(self, 11)

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.get_safe("i18n"):
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        feature = lambda option: "enabled" if option else "disabled"
        true_false = lambda option: "true" if option else "false"
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["bpf"] = "disabled"  # Requires Clang
        tc.project_options["gconv"] = "enabled"
        tc.project_options["jpeg"] = feature(self.options.with_jpeg)
        tc.project_options["libdvbv5"] = feature(self.options.build_libdvbv5)
        tc.project_options["v4l-plugins"] = true_false(self.options.build_plugins)
        tc.project_options["v4l-wrappers"] = true_false(self.options.build_wrappers)
        # Disable executables to simplify the recipe
        tc.project_options["v4l-utils"] = "false"
        tc.project_options["qv4l2"] = "disabled"
        tc.project_options["qvidcap"] = "disabled"
        tc.project_options["v4l2-tracer"] = "disabled"
        # Doxygen options
        tc.project_options["doxygen-doc"] = "disabled"
        tc.project_options["doxygen-html"] = "false"
        tc.project_options["doxygen-man"] = "false"
        # tc.project_options["gconvsysdir"] = ""
        # tc.project_options["libv4l1subdir"] = ""
        # tc.project_options["libv4l2subdir"] = ""
        # tc.project_options["libv4lconvertsubdir"] = ""
        # tc.project_options["systemdsystemunitdir"] = ""
        # tc.project_options["udevdir"] = ""
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        if not self.options.get_safe("i18n"):
            save(self, os.path.join(self.source_folder, "po", "meson.build"), "")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING.libv4l", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.options.build_libdvbv5:
            copy(self, "COPYING.libdvbv5", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)
        fix_apple_shared_install_name(self)

    def package_info(self):
        # libv4lconvert: v4l format conversion library
        self.cpp_info.components["libv4lconvert"].libs = ["v4lconvert"]
        if self.options.with_jpeg:
            self.cpp_info.components["libv4lconvert"].requires = ["libjpeg-meta::jpeg"]
        self.cpp_info.components["libv4lconvert"].system_libs = ["m", "rt"]

        # libv4l2: v4l2 device access library
        self.cpp_info.components["libv4l2"].set_property("pkg_config_name", "libv4l2")
        self.cpp_info.components["libv4l2"].libs = ["v4l2"]
        self.cpp_info.components["libv4l2"].requires = ["libv4lconvert"]
        self.cpp_info.components["libv4l2"].system_libs = ["dl", "pthread"]

        # libv4l2rds: v4l2 RDS decode library
        self.cpp_info.components["libv4l2rds"].set_property("pkg_config_name", "libv4l2rds")
        self.cpp_info.components["libv4l2rds"].libs = ["v4l2rds"]
        self.cpp_info.components["libv4l2rds"].system_libs = ["pthread"]

        # libv4l1: v4l1 compatibility library
        self.cpp_info.components["libv4l1"].set_property("pkg_config_name", "libv4l1")
        self.cpp_info.components["libv4l1"].libs = ["v4l1"]
        self.cpp_info.components["libv4l1"].requires = ["libv4l2"]
        self.cpp_info.components["libv4l1"].system_libs = ["pthread"]

        if self.options.build_libdvbv5:
            # libdvbv5: DVBv5 utility library
            self.cpp_info.components["libdvbv5"].set_property("pkg_config_name", "libdvbv5")
            self.cpp_info.components["libdvbv5"].libs = ["dvbv5"]
            self.cpp_info.components["libdvbv5"].requires = ["libudev::libudev"]
            self.cpp_info.components["libdvbv5"].system_libs = ["m", "rt", "pthread"]
            if self.options.i18n:
                self.cpp_info.components["libdvbv5"].resdirs = ["share"]
