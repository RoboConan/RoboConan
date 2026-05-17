import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson

required_conan_version = ">=2.4"


class GumboParserConan(ConanFile):
    name = "gumbo-parser"
    description = "An HTML5 parsing library in pure C99"
    topics = ("parser", "html", "html5")
    homepage = "https://codeberg.org/gumbo-parser/gumbo-parser"
    license = "Apache-2.0"
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
        self.tool_requires("meson/[^1.2.3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["tests"] = False
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", os.path.join(self.source_folder, "doc"), os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "gumbo")
        self.cpp_info.libs = ["gumbo"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
