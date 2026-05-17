import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class PackageConan(ConanFile):
    name = "libva"
    description = "Libva is an implementation for VA-API"
    license = "MIT"
    homepage = "https://github.com/intel/libva"
    topics = ("VA-API", "Video", "Acceleration")
    provides = "vaapi"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_drm": [True, False],
        "with_x11": [True, False],
        "with_glx": [True, False],
        "with_wayland": [True, False],
        "with_win32": [True, False],
    }
    default_options = {
        "with_drm": True,
        "with_x11": True,
        "with_glx": True,
        "with_wayland": True,
        "with_win32": True,
    }
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os != "Windows":
            del self.options.with_win32
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_x11
            del self.options.with_glx
            del self.options.with_drm
        if self.settings.os != "Linux":
            del self.options.with_wayland

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("with_x11"):
            self.requires("xorg/system")
        if self.options.get_safe("with_drm"):
            self.requires("libdrm/[~2.4.119]")
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22.0]")
        if self.options.get_safe("with_glx"):
            self.requires("opengl/system")

    def validate(self):
        if self.options.get_safe("with_glx") and not self.options.get_safe("with_x11"):
            raise ConanInvalidConfiguration(f"{self.ref} requires x11 when glx is enabled")
        if not self.options.get_safe("with_drm") and not self.options.get_safe("with_x11") and not self.options.get_safe("with_wayland") and not self.options.get_safe("with_win32"):
            raise ConanInvalidConfiguration(f"{self.ref} cannot be built without at least one backend dev files.")

    def build_requirements(self):
        if self.options.get_safe("with_wayland"):
            self.tool_requires("wayland/<host_version>")
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if self.options.get_safe("with_wayland") and can_run(self):
            # Workaround for libxml2.so not being found by wayland-scanner
            VirtualRunEnv(self).generate(scope="build")

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["disable_drm"] = not self.options.get_safe("with_drm")
        for opt in ["with_x11", "with_glx", "with_wayland", "with_win32"]:
            tc.project_options[opt] = "yes" if self.options.get_safe(opt) else "no"
        tc.generate()

        pkg_config_deps = PkgConfigDeps(self)
        pkg_config_deps.build_context_activated.append("wayland")
        pkg_config_deps.build_context_folder = os.path.join(self.generators_folder, "build")
        pkg_config_deps.generate()

        # required for dependency(..., native: true) in meson.build
        env = Environment()
        env.define_path("PKG_CONFIG_FOR_BUILD", self.conf.get("tools.gnu:pkg_config", default="pkgconf", check_type=str))
        env.define_path("PKG_CONFIG_PATH_FOR_BUILD", os.path.join(self.generators_folder, "build"))
        env.vars(self).save_script("pkg_config_for_build_env")

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.components["va"].libs = ["va"]
        self.cpp_info.components["va"].set_property("pkg_config_name", "libva")

        if self.options.get_safe("with_drm"):
            self.cpp_info.components["drm"].libs = ["va-drm"]
            self.cpp_info.components["drm"].set_property("pkg_config_name", "libva-drm")
            self.cpp_info.components["drm"].requires = ["va", "libdrm::libdrm_libdrm"]

        if self.options.get_safe("with_x11"):
            self.cpp_info.components["x11"].libs = ["va-x11"]
            self.cpp_info.components["x11"].set_property("pkg_config_name", "libva-x11")
            self.cpp_info.components["x11"].requires = [
                "va",
                "xorg::x11",
                "xorg::x11-xcb",
                "xorg::xcb",
                "xorg::xcb-dri3",
                "xorg::xext",
                "xorg::xfixes",
            ]

        if self.options.get_safe("with_glx"):
            self.cpp_info.components["glx"].libs = ["va-glx"]
            self.cpp_info.components["glx"].set_property("pkg_config_name", "libva-glx")
            self.cpp_info.components["glx"].requires = ["va", "opengl::opengl"]

        if self.options.get_safe("with_wayland"):
            self.cpp_info.components["wayland"].libs = ["va-wayland"]
            self.cpp_info.components["wayland"].set_property("pkg_config_name", "libva-wayland")
            self.cpp_info.components["wayland"].requires = ["va", "wayland::wayland-client"]

        if self.options.get_safe("with_win32"):
            self.cpp_info.components["win32"].libs = ["va_win32"]
            self.cpp_info.components["win32"].set_property("pkg_config_name", "libva-win32")
            self.cpp_info.components["win32"].requires = ["va"]
