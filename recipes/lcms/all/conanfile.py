import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
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
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        # JPEG and TIFF are used only by command-line utilities, which are not packaged.
        tc.project_options["jpeg"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["tiff"] = "disabled"
        tc.project_options["utils"] = False
        # Optional installed plugins are GPL-3.0; this package remains the MIT-licensed core library.
        tc.project_options["fastfloat"] = False
        tc.project_options["threaded"] = False
        tc.project_options["versionedlibs"] = self.settings.os != "Android"
        tc.generate()

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
