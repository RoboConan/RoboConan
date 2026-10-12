import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson

required_conan_version = ">=2.4"


class LibdrmConan(ConanFile):
    name = "libdrm"
    description = ("User space library for accessing the Direct Rendering Manager, "
                   "on operating systems that support the ioctl interface")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/mesa/drm"
    topics = ("graphics",)
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "intel": [True, False],
        "radeon": [True, False],
        "amdgpu": [True, False],
        "nouveau": [True, False],
        "vmwgfx": [True, False],
        "omap": [True, False],
        "exynos": [True, False],
        "freedreno": [True, False],
        "tegra": [True, False],
        "vc4": [True, False],
        "etnaviv": [True, False],
        "valgrind": [True, False],
        "freedreno-kgsl": [True, False],
        "udev": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "intel": True,
        "radeon": True,
        "amdgpu": True,
        "nouveau": True,
        "vmwgfx": True,
        "omap": False,
        "exynos": False,
        "freedreno": True,
        "tegra": False,
        "vc4": True,
        "etnaviv": False,
        "valgrind": False,
        "freedreno-kgsl": False,
        "udev": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.intel:
            self.requires("libpciaccess/[>=0.17 <1]")
        if self.settings.os == "Linux":
            self.requires("linux-headers-generic/[^6.5]")

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            raise ConanInvalidConfiguration("libdrm supports only Linux or FreeBSD")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["cairo-tests"] = "disabled"
        tc.project_options["install-test-programs"] = "false"
        tc.project_options["freedreno-kgsl"] = "true" if self.options.get_safe("freedreno-kgsl") else "false"
        tc.project_options["udev"] = "true" if self.options.udev else "false"
        for o in ["intel", "radeon", "amdgpu", "nouveau", "vmwgfx", "omap",
                  "exynos", "freedreno", "tegra", "vc4", "etnaviv", "valgrind"]:
            tc.project_options[o] = "enabled" if self.options.get_safe(o) else "disabled"
        tc.project_options["man-pages"] = "disabled"
        tc.generate()

        tc = PkgConfigDeps(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        mkdir(self, os.path.join(self.package_folder, "licenses"))
        # Extract the License/s from the header to a file
        tmp = load(self, os.path.join(self.source_folder, "include", "drm", "drm.h"))
        license_contents = re.search(r"\*/.*(/\*(\*(?!/)|[^*])*\*/)", tmp, re.DOTALL)[1]
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), license_contents)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "none")

        self.cpp_info.components["libdrm_libdrm"].set_property("pkg_config_name", "libdrm")
        self.cpp_info.components["libdrm_libdrm"].libs = ["drm"]
        self.cpp_info.components["libdrm_libdrm"].includedirs.append("include/libdrm")
        if self.settings.os == "Linux":
            self.cpp_info.components["libdrm_libdrm"].requires = ["linux-headers-generic::linux-headers-generic"]

        if self.options.vc4:
            self.cpp_info.components["libdrm_vc4"].set_property("pkg_config_name", "libdrm_vc4")
            self.cpp_info.components["libdrm_vc4"].requires = ["libdrm_libdrm"]

        if self.options.freedreno:
            self.cpp_info.components["libdrm_freedreno"].set_property("pkg_config_name", "libdrm_freedreno")
            self.cpp_info.components["libdrm_freedreno"].libs = ["drm_freedreno"]
            self.cpp_info.components["libdrm_freedreno"].includedirs.extend(["include/libdrm", "include/freedreno"])
            self.cpp_info.components["libdrm_freedreno"].requires = ["libdrm_libdrm"]

        if self.options.amdgpu:
            self.cpp_info.components["libdrm_amdgpu"].set_property("pkg_config_name", "libdrm_amdgpu")
            self.cpp_info.components["libdrm_amdgpu"].libs = ["drm_amdgpu"]
            self.cpp_info.components["libdrm_amdgpu"].includedirs.append("include/libdrm")
            self.cpp_info.components["libdrm_amdgpu"].requires = ["libdrm_libdrm"]

        if self.options.nouveau:
            self.cpp_info.components["libdrm_nouveau"].set_property("pkg_config_name", "libdrm_nouveau")
            self.cpp_info.components["libdrm_nouveau"].libs = ["drm_nouveau"]
            self.cpp_info.components["libdrm_nouveau"].includedirs.extend(["include/libdrm", "include/libdrm/nouveau"])
            self.cpp_info.components["libdrm_nouveau"].requires = ["libdrm_libdrm"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["libdrm_nouveau"].system_libs = ["pthread"]

        if self.options.intel:
            self.cpp_info.components["libdrm_intel"].set_property("pkg_config_name", "libdrm_intel")
            self.cpp_info.components["libdrm_intel"].libs = ["drm_intel"]
            self.cpp_info.components["libdrm_intel"].includedirs.append("include/libdrm")
            self.cpp_info.components["libdrm_intel"].requires = ["libdrm_libdrm", "libpciaccess::libpciaccess"]

        if self.options.radeon:
            self.cpp_info.components["libdrm_radeon"].set_property("pkg_config_name", "libdrm_radeon")
            self.cpp_info.components["libdrm_radeon"].libs = ["drm_radeon"]
            self.cpp_info.components["libdrm_radeon"].includedirs.append("include/libdrm")
            self.cpp_info.components["libdrm_radeon"].requires = ["libdrm_libdrm"]
