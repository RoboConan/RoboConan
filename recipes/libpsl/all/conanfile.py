import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class LibPslConan(ConanFile):
    name = "libpsl"
    description = "C library for the Public Suffix List"
    homepage = "https://github.com/rockdaboot/libpsl"
    topics = ("psl", "suffix", "TLD", "gTLD", ".com", ".net")
    license = "GPL-2.0-or-later"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_idna": [False, "icu", "libidn", "libidn2"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_idna": "icu",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_idna == "icu":
            self.requires("icu/[*]")
        elif self.options.with_idna == "libidn":
            self.requires("libidn/1.36")
        elif self.options.with_idna == "libidn2":
            self.requires("libidn2/2.3.0")
        if self.options.with_idna in ("libidn", "libidn2"):
            self.requires("libunistring/[^1.1]")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    @property
    def _idna_option(self):
        return {
            "False": "no",
            "icu": "libicu",
        }.get(str(self.options.with_idna), str(self.options.with_idna))

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["runtime"] = self._idna_option
        if Version(self.version) >= "0.21.5":
            tc.project_options["builtin"] = "true" if self.options.with_idna else "false"
            tc.project_options["tests"] = "false"  # disable tests and fuzzes
        else:
            tc.project_options["builtin"] = self._idna_option
        if not self.options.shared:
            tc.preprocessor_definitions["PSL_STATIC"] = "1"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libpsl")
        self.cpp_info.libs = ["psl"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32"]
        if not self.options.shared:
            self.cpp_info.defines = ["PSL_STATIC"]
