import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class LibSixelConan(ConanFile):
    name = "libsixel"
    description = ("A SIXEL encoder/decoder implementation derived from kmiya's sixel"
                   " (https://github.com/saitoha/sixel).")
    license = "MIT"
    homepage = "https://github.com/libsixel/libsixel"
    topics = "sixel"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_curl": [True, False],
        "with_gdk_pixbuf2": [True, False],
        "with_gd": [True, False],
        "with_jpeg": [True, False],
        "with_png": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_curl": True,
        "with_gd": False,
        "with_gdk_pixbuf2": False,
        "with_jpeg": True,
        "with_png": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_curl:
            self.requires("libcurl/[>=7.78.0 <9]")
        if self.options.with_gd:
            self.requires("libgd/2.3.3")
        if self.options.with_gdk_pixbuf2:
            self.requires("gdk-pixbuf/[^2.42.10]")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.with_png:
            self.requires("libpng/[~1.6]")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration(f"{self.ref} does not support Visual Studio")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options = {
            "libcurl": "enabled" if self.options.with_curl else "disabled",
            "gd": "enabled" if self.options.with_gd else "disabled",
            "gdk-pixbuf2": "enabled" if self.options.with_gdk_pixbuf2 else "disabled",
            "img2sixel": "disabled",
            "sixel2png": "disabled",
            "python2": "disabled",
            "libdir": "lib",
        }
        tc.generate()
        tc = PkgConfigDeps(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE*", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
            rm(self, "*.lib", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*.dll", os.path.join(self.package_folder, "bin"))
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))
            rm(self, "*.dylib", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.libs = ["sixel"]
