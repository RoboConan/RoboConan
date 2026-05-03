import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv, Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class WaylandConan(ConanFile):
    name = "wayland"
    description = (
        "Wayland is a project to define a protocol for a compositor to talk to "
        "its clients as well as a library implementation of the protocol"
    )
    topics = "protocol", "compositor", "display"
    homepage = "https://wayland.freedesktop.org"
    license = "MIT"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_libraries": [True, False],
        "enable_dtd_validation": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_libraries": True,
        "enable_dtd_validation": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("wayland-protocols/[^1.42]", visible=True)
        if self.options.enable_libraries:
            self.requires("libffi/[^3.4.4]")
        if self.options.enable_dtd_validation:
            self.requires("libxml2/[^2.12.5]")
        self.requires("expat/[>=2.6.2 <3]")

    def validate(self):
      if self.settings.os not in ("Linux", "Android"):
            raise ConanInvalidConfiguration(f"{self.ref} only supports Linux or Android")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.4.0 <2]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if not can_run(self):
            self.tool_requires(str(self.ref))

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        if can_run(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["libdir"] = "lib"
        tc.project_options["libraries"] = self.options.enable_libraries
        tc.project_options["dtd_validation"] = self.options.enable_dtd_validation
        tc.project_options["documentation"] = False
        tc.project_options["scanner"] = True
        if not can_run(self):
            tc.build_pkg_config_path = os.path.join(self.generators_folder, "build")
        tc.generate()

        deps = PkgConfigDeps(self)
        # For cross-compilation support
        deps.build_context_activated = [dep.ref.name for dep, _ in self.dependencies.build.items()]
        deps.build_context_folder = os.path.join(self.generators_folder, "build")
        deps.generate()

        if not can_run(self):
            # required for dependency(..., native: true) in meson.build
            env = Environment()
            env.define_path("PKG_CONFIG_FOR_BUILD", self.conf.get("tools.gnu:pkg_config", default="pkgconf", check_type=str))
            env.define_path("PKG_CONFIG_PATH_FOR_BUILD", os.path.join(self.generators_folder, "build"))
            env.vars(self).save_script("pkg_config_for_build_env")

    def _patch_sources(self):
        replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                        "subdir('tests')", "#subdir('tests')")

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        pkg_config_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        rmdir(self, pkg_config_dir)

    def package_info(self):
        self.cpp_info.components["wayland-scanner"].set_property("pkg_config_name", "wayland-scanner")
        self.cpp_info.components["wayland-scanner"].resdirs = ["share"]
        self.cpp_info.components["wayland-scanner"].includedirs = []
        self.cpp_info.components["wayland-scanner"].libdirs = []
        self.cpp_info.components["wayland-scanner"].set_property("component_version", self.version)
        self.cpp_info.components["wayland-scanner"].requires = ["expat::expat"]
        if self.options.enable_dtd_validation:
            self.cpp_info.components["wayland-scanner"].requires.append("libxml2::libxml2")
        pkgconfig_variables = {
            'datarootdir': '${prefix}/share',
            'pkgdatadir': '${datarootdir}/wayland',
            'bindir': '${prefix}/bin',
            'wayland_scanner': '${bindir}/wayland-scanner',
        }
        self.cpp_info.components["wayland-scanner"].set_property(
            "pkg_config_custom_content",
            "\n".join(f"{key}={value}" for key,value in pkgconfig_variables.items()))

        if self.options.enable_libraries:
            self.cpp_info.components["wayland-server"].libs = ["wayland-server"]
            self.cpp_info.components["wayland-server"].set_property("pkg_config_name", "wayland-server")
            self.cpp_info.components["wayland-server"].requires = ["libffi::libffi"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["wayland-server"].system_libs = ["pthread", "m"]

            self.cpp_info.components["wayland-server"].resdirs = ["share"]
            if self.settings.os == "Linux":
                self.cpp_info.components["wayland-server"].system_libs += ["rt"]
            self.cpp_info.components["wayland-server"].set_property("component_version", self.version)
            pkgconfig_variables = {
                'datarootdir': '${prefix}/share',
                'pkgdatadir': '${datarootdir}/wayland',
            }
            self.cpp_info.components["wayland-server"].set_property(
                "pkg_config_custom_content",
                "\n".join(f"{key}={value}" for key, value in pkgconfig_variables.items()))

            self.cpp_info.components["wayland-client"].libs = ["wayland-client"]
            self.cpp_info.components["wayland-client"].set_property("pkg_config_name", "wayland-client")
            self.cpp_info.components["wayland-client"].requires = ["libffi::libffi", "wayland-protocols::wayland-protocols"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["wayland-client"].system_libs = ["pthread", "m"]
            self.cpp_info.components["wayland-client"].resdirs = ["share"]
            if self.settings.os == "Linux":
                self.cpp_info.components["wayland-client"].system_libs += ["rt"]
            self.cpp_info.components["wayland-client"].set_property("component_version", self.version)
            pkgconfig_variables = {
                'datarootdir': '${prefix}/share',
                'pkgdatadir': '${datarootdir}/wayland',
            }
            self.cpp_info.components["wayland-client"].set_property(
                "pkg_config_custom_content",
                "\n".join(f"{key}={value}" for key, value in pkgconfig_variables.items()))

            self.cpp_info.components["wayland-cursor"].libs = ["wayland-cursor"]
            self.cpp_info.components["wayland-cursor"].set_property("pkg_config_name", "wayland-cursor")
            self.cpp_info.components["wayland-cursor"].requires = ["wayland-client"]
            self.cpp_info.components["wayland-cursor"].set_property("component_version", self.version)

            self.cpp_info.components["wayland-egl"].libs = ["wayland-egl"]
            self.cpp_info.components["wayland-egl"].set_property("pkg_config_name", "wayland-egl")
            self.cpp_info.components["wayland-egl"].requires = ["wayland-client"]
            self.cpp_info.components["wayland-egl"].set_property("component_version", "18.1.0")

            self.cpp_info.components["wayland-egl-backend"].set_property("pkg_config_name", "wayland-egl-backend")
            self.cpp_info.components["wayland-egl-backend"].set_property("component_version", "3")

        aclocal_path = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.append_path("ACLOCAL_PATH", aclocal_path)
