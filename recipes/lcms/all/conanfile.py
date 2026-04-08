import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class LcmsConan(ConanFile):
    name = "lcms"
    description = "A free, open source, CMM engine."
    license = "MIT"
    homepage = "https://github.com/mm2/Little-CMS"
    topics = ("littlecms", "little-cms", "cmm", "icc", "cmm-engine", "color-management-engine")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "jpeg": [True, False],
        "tiff": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "jpeg": False,
        "tiff": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.tiff:
            self.requires("libtiff/[^4.5]")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if self.options.jpeg or self.options.tiff:
            if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
                self.tool_requires("pkgconf/[^2.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        def feature(v): return "enabled" if v else "disabled"
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["jpeg"] = feature(self.options.jpeg)
        tc.project_options["tiff"] = feature(self.options.tiff)
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "lcms2")
        self.cpp_info.libs = ["lcms2"]
        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.defines.append("CMS_DLL")
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs.extend(["m", "pthread"])
