import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class FontconfigConan(ConanFile):
    name = "fontconfig"
    license = "MIT"
    description = "Fontconfig is a library for configuring and customizing font access"
    homepage = "https://gitlab.freedesktop.org/fontconfig/fontconfig"
    topics = ("fonts", "freedesktop")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "xml_backend": ["expat", "libxml2"],
        "use_system_fonts": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "xml_backend": "libxml2",
        "use_system_fonts": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.options.use_system_fonts

    def requirements(self):
        self.requires("freetype/[^2.13.2]")
        if self.options.xml_backend == "libxml2":
            self.requires("libxml2/[^2.12.5]")
        elif self.options.xml_backend == "expat":
            self.requires("expat/[>=2.6.2 <3]")

    def build_requirements(self):
        self.tool_requires("gperf/3.1")
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["nls"] = "enabled" if self.options.i18n else "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["tools"] = "disabled"
        tc.project_options["xml-backend"] = self.options.xml_backend.value
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rm(self, "*.pdb", self.package_folder, recursive=True)
        rm(self, "*.conf", os.path.join(self.package_folder, "etc", "fonts", "conf.d"))
        rm(self, "*.def", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "Fontconfig")
        self.cpp_info.set_property("cmake_target_name", "Fontconfig::Fontconfig")
        self.cpp_info.set_property("pkg_config_name", "fontconfig")
        self.cpp_info.libs = ["fontconfig"]
        self.cpp_info.resdirs = ["etc", "share"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs.extend(["m", "pthread"])

        if not self.options.use_system_fonts:
            fontconfig_path = os.path.join(self.package_folder, "etc", "fonts")
            self.runenv_info.append_path("FONTCONFIG_PATH", fontconfig_path)
