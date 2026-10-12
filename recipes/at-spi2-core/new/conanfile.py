import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class AtSpi2CoreConan(ConanFile):
    name = "at-spi2-core"
    description = "It provides a Service Provider Interface for the Assistive Technologies available on the GNOME platform and a library against which applications can be linked"
    topics = ("atk", "accessibility")
    homepage = "https://gitlab.gnome.org/GNOME/at-spi2-core/"
    license = "LGPL-2.1-or-later"

    provides = "at-spi2-atk", "atk"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "with_x11": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "with_x11": True,
        "with_introspection": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_x11

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_introspection:
            self.requires("gobject-introspection/[^1.82]", options={"build_introspection_data": True})
            self.requires("glib-gir/[^2.82]")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.requires("dbus/[^1.15]")
        if self.options.get_safe("with_x11"):
            self.requires("xorg/system")

    def validate(self):
        if self.options.shared and not self.dependencies["glib"].options.shared:
            raise ConanInvalidConfiguration(
                "Linking a shared library against static glib can cause unexpected behaviour."
            )

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("glib/<host_version>")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "meson.build", "subdir('tests')", "#subdir('tests')")
        replace_in_file(self, os.path.join(self.source_folder, "bus", "meson.build"),
                        "if x11_dep.found()",
                        "if get_option('x11').enabled()")
        replace_in_file(self, "meson.build",
                        "libxml_dep = dependency('libxml-2.0', version: libxml_req_version)",
                        "#libxml_dep = dependency('libxml-2.0', version: libxml_req_version)")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["introspection"] = "enabled" if self.options.with_introspection else "disabled"
        tc.project_options["x11"] = "enabled" if self.options.get_safe("with_x11") else "disabled"
        if self.settings.os != "Linux":
            tc.project_options["atk_only"] = "true"
        tc.project_options["docs"] = "false"
        if self.options.with_introspection and not is_msvc(self):
            # g-ir-scanner tends to use system libgirepository-1.0.so otherwise
            tc.extra_ldflags.append(f"-L{self.dependencies['gobject-introspection'].cpp_info.libdir}")
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        if not self.options.i18n:
            save(self, os.path.join(self.source_folder, "po", "meson.build"), "")
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "etc"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["atspi"].set_property("pkg_config_name", "atspi-2")
            self.cpp_info.components["atspi"].libs = ["atspi"]
            self.cpp_info.components["atspi"].includedirs = ["include/at-spi-2.0"]
            self.cpp_info.components["atspi"].resdirs = ["share"]
            self.cpp_info.components["atspi"].requires = ["dbus::dbus", "glib::glib-2.0", "glib::gobject-2.0"]
            if self.options.with_x11:
                self.cpp_info.components["atspi"].requires.extend(["xorg::x11", "xorg::xtst", "xorg::xi"])

        self.cpp_info.components["atk"].set_property("pkg_config_name", "atk")
        self.cpp_info.components["atk"].libs = ["atk-1.0"]
        self.cpp_info.components["atk"].includedirs = ["include/atk-1.0"]
        self.cpp_info.components["atk"].resdirs = ["share"]
        self.cpp_info.components["atk"].requires = ["glib::glib-2.0", "glib::gobject-2.0"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["atk-bridge"].set_property("pkg_config_name", "atk-bridge-2.0")
            self.cpp_info.components["atk-bridge"].libs = ["atk-bridge-2.0"]
            self.cpp_info.components["atk-bridge"].includedirs = [os.path.join("include", "at-spi2-atk", "2.0")]
            self.cpp_info.components["atk-bridge"].resdirs = ["share"]
            self.cpp_info.components["atk-bridge"].requires = ["atspi", "atk", "glib::gmodule-2.0"]

        if self.options.with_introspection:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["atk"].requires.extend(["gobject-introspection::gobject-introspection", "glib-gir::glib-gir"])
                self.cpp_info.components["atspi"].requires.extend(["gobject-introspection::gobject-introspection", "glib-gir::glib-gir"])
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
