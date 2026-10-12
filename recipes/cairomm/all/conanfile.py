import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class CairommConan(ConanFile):
    name = "cairomm"
    description = "cairomm is a C++ wrapper for the cairo graphics library."
    license = "LGPL-2.0"
    homepage = "https://www.cairographics.org/cairomm/"
    topics = ["cairo", "wrapper", "graphics"]
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

    python_requires = "conan-utils/latest"

    @property
    def _abi_version(self):
        return "1.16" if Version(self.version) >= "1.16.0" else "1.0"

    @property
    def _min_cppstd(self):
        return 17 if self._abi_version == "1.16" else 11

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.shared:
            self.options["cairo"].shared = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cairo/[^1.18.0]", transitive_headers=True, transitive_libs=True)
        if self._abi_version == "1.16":
            self.requires("libsigcpp/[^3.0.7]", transitive_headers=True, transitive_libs=True)
        else:
            self.requires("libsigcpp/[^2.10.8]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)
        if self.options.shared and not self.dependencies["cairo"].options.shared:
            raise ConanInvalidConfiguration(
                "Linking against static cairo would cause shared cairomm to link "
                "against static glib which can cause problems."
            )

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = PkgConfigDeps(self)
        tc.generate()
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options = {
            "build-examples": "false",
            "build-documentation": "false",
            "build-tests": "false",
            "msvc14x-parallel-installable": "false",
            "default_library": "shared" if self.options.shared else "static",
            "libdir": "lib",
        }
        if not self.options.shared:
            tc.preprocessor_definitions["CAIROMM_STATIC_LIB"] = "1"
        tc.generate()

    def _patch_sources(self):
        if is_msvc(self):
            # when using cpp_std=c++11 the /permissive- flag is added which
            # attempts enforcing standard conformant c++ code
            # the problem is that older versions of Windows SDK is not standard
            # conformant! see:
            # https://developercommunity.visualstudio.com/t/error-c2760-in-combaseapih-with-windows-sdk-81-and/185399
            replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                            "cpp_std=c++",
                            "cpp_std=vc++")

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"), recursive=True)
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        name = f"cairomm-{self._abi_version}"
        self.cpp_info.components[name].set_property("pkg_config_name", name)
        self.cpp_info.components[name].includedirs += [
            os.path.join("include", name),
            os.path.join("lib", name, "include"),
        ]
        self.cpp_info.components[name].libs = [name]
        self.cpp_info.components[name].requires = ["cairo::cairo_", "libsigcpp::libsigcpp"]
        if not self.options.shared:
            self.cpp_info.components[name].defines = ["CAIROMM_STATIC_LIB"]
        if is_apple_os(self):
            self.cpp_info.components[name].frameworks = ["CoreFoundation"]

        # https://gitlab.freedesktop.org/cairo/cairomm/-/blob/1.18.0/data/meson.build?ref_type=tags#L30-31
        cairo_components = self.dependencies["cairo"].cpp_info.components
        for cairomm_mod in [
            "ft",
            "pdf",
            "png",
            "ps",
            "quartz",
            "quartz-font",
            "quartz-image",
            "svg",
            "win32",
            "win32-font",
            "xlib",
            "xlib-xrender",
        ]:
            if f"cairo-{cairomm_mod}" in cairo_components:
                component = f"cairomm-{cairomm_mod}-{self._abi_version}"
                self.cpp_info.components[component].set_property("pkg_config_name", component)
                self.cpp_info.components[component].requires = [name, f"cairo::cairo-{cairomm_mod}"]
