import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class LibproxyConan(ConanFile):
    name = "libproxy"
    description = "libproxy is a library that provides automatic proxy configuration management."
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libproxy/libproxy"
    topics = ("proxy", "network")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_duktape": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_duktape": True,
        "with_introspection": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.71.3]")
        self.requires("libcurl/[>=7.78.0 <9]")
        self.requires("gsettings-desktop-schemas/[*]")
        if self.options.with_duktape:
            self.requires("duktape/[^2.7.0]")
        if self.options.with_introspection:
            self.requires("glib-gir/[^2.82]")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["docs"] = "false"
        tc.project_options["tests"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["curl"] = "true"
        tc.project_options["introspection"] = self.options.with_introspection
        tc.project_options["release"] = self.settings.build_type != "Debug"
        tc.project_options["pacrunner-duktape"] = self.options.with_duktape
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.components["libproxy-1.0"].set_property("pkg_config_name", "libproxy-1.0")
        self.cpp_info.components["libproxy-1.0"].libs = ["proxy"]
        self.cpp_info.components["libproxy-1.0"].includedirs.append(os.path.join("include", "libproxy"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libproxy-1.0"].system_libs.extend(["m", "pthread", "dl"])
        elif self.settings.os == "Windows":
            self.cpp_info.components["libproxy-1.0"].system_libs.extend(["ws2_32"])
        self.cpp_info.components["libproxy-1.0"].requires = ["glib::gobject-2.0", "pxbackend-1.0"]

        if self.options.with_introspection:
            self.cpp_info.components["libproxy-1.0"].requires.append("glib-gir::glib-gir")
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))

        self.cpp_info.components["pxbackend-1.0"].libs = ["pxbackend-1.0"]
        self.cpp_info.components["pxbackend-1.0"].libdirs = [os.path.join("lib", "libproxy")]
        self.cpp_info.components["pxbackend-1.0"].requires = [
            "libcurl::libcurl",
            "gsettings-desktop-schemas::gsettings-desktop-schemas",
        ]
        if self.options.with_duktape:
            self.cpp_info.components["pxbackend-1.0"].requires.append("duktape::duktape")
        if is_apple_os(self):
            self.cpp_info.components["pxbackend-1.0"].frameworks = ["Foundation", "SystemConfiguration"]
