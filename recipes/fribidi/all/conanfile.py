import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class FriBiDiCOnan(ConanFile):
    name = "fribidi"
    description = "The Free Implementation of the Unicode Bidirectional Algorithm"
    license = "LGPL-2.1"
    homepage = "https://github.com/fribidi/fribidi"
    topics = ("unicode", "bidirectional", "text")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_deprecated": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_deprecated": True,
    }
    languages = ["C"]
    implements = ["auto_shared_fpic"]

    python_requires = "conan-utils/latest"

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["deprecated"] = self.options.with_deprecated
        tc.project_options["docs"] = False
        tc.project_options["bin"] = False
        tc.project_options["tests"] = False
        tc.generate()
        if cross_building(self):
            # required for gen-unicode-version build tool
            MesonToolchain(self, native=True).generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "fribidi")
        self.cpp_info.libs = ["fribidi"]
        self.cpp_info.includedirs.append(os.path.join("include", "fribidi"))
        if not self.options.shared:
            self.cpp_info.defines.append("FRIBIDI_LIB_STATIC")
