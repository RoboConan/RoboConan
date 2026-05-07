import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps, AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class LibX11Conan(ConanFile):
    name = "libx11"
    description = "Core X11 protocol client library"
    license = "MIT AND MIT-open-group AND X11 AND DocumentRef-COPYING:LicenseRef-X11-other"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libx11"
    topics = ("xorg", "x11")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_unix_transport": [True, False],
        "enable_tcp_transport": [True, False],
        "enable_ipv6": [True, False],
        "enable_specs": [True, False],
        "enable_year2038": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_unix_transport": True,
        "enable_tcp_transport": True,
        "enable_ipv6": True,
        "enable_specs": True,
        "enable_year2038": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        copy(self, "conan-findx11.cmake", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("xorg-proto/[>=2024.1]", transitive_headers=True)
        self.requires("libxcb/[^1.17.0]", transitive_headers=True)
        self.requires("xtrans/[^1.5.0]")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported.")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        self.tool_requires("xorg-macros/[^1.20.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

        yes_no = lambda v: "yes" if v else "no"
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--enable-unix-transport={yes_no(self.options.enable_unix_transport)}",
            f"--enable-tcp-transport={yes_no(self.options.enable_tcp_transport)}",
            f"--enable-ipv6={yes_no(self.options.enable_ipv6)}",
            f"--enable-loadable-i18n={yes_no(self.options.enable_specs)}",
            f"--enable-year2038={yes_no(self.options.enable_year2038)}",
            "--enable-xlocaledir",  # For XLOCALEDIR env var support
            "--disable-xf86bigfont",  # deprecated
            # Disable optional tools
            "--without-fop",
            "--without-perl",
            "--without-xsltproc",
            "--without-xmlto",
        ])
        if not can_run(self):
            # Skip a check that tries to run a test executable
            tc.configure_args.append("xorg_cv_malloc0_returns_null=no")
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        fix_apple_shared_install_name(self)
        copy(self, "conan-findx11.cmake",
             self.export_sources_folder,
             os.path.join(self.package_folder, "lib", "cmake", "X11"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "X11")
        self.cpp_info.set_property("pkg_config_name", "_x11_do_not_use")

        self.cpp_info.components["x11"].set_property("pkg_config_name", "x11")
        self.cpp_info.components["x11"].set_property("cmake_target_name", "X11::X11")
        self.cpp_info.components["x11"].libs = ["X11"]
        self.cpp_info.components["x11"].requires = ["xorg-proto::xorg-proto", "libxcb::xcb", "xtrans::xtrans"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["x11"].system_libs = ["pthread"]
            self.cpp_info.components["x11"].set_property("pkg_config_custom_content", "xthreadlib=-lpthread")
        elif self.settings.os == "Windows":
            self.cpp_info.components["x11"].system_libs = ["ws2_32"]

        self.cpp_info.components["x11-xcb"].set_property("pkg_config_name", "x11-xcb")
        self.cpp_info.components["x11-xcb"].set_property("cmake_target_name", "X11::X11_xcb")
        self.cpp_info.components["x11-xcb"].libs = ["X11-xcb"]
        self.cpp_info.components["x11-xcb"].requires = ["x11"]

        # FindX11.cmake compatibility module
        module_dir = os.path.join("lib", "cmake", "X11")
        self.cpp_info.builddirs.append(module_dir)
        cmake_module = os.path.join(module_dir, "conan-findx11.cmake")
        self.cpp_info.set_property("cmake_build_modules", [cmake_module])

        # Set env vars for relocated module and resource files
        self.runenv_info.define_path("XCMSDB", os.path.join(self.package_folder, "share", "X11", "Xcms.txt"))
        self.runenv_info.define_path("XERRORDB", os.path.join(self.package_folder, "share", "X11", "XErrorDB"))
        self.runenv_info.define_path("XLOCALEDIR", os.path.join(self.package_folder, "share", "X11", "locale"))
        self.runenv_info.define_path("XLOCALELIBDIR", os.path.join(self.package_folder, "lib", "X11", "locale"))
        # Not installed?
        # self.runenv_info.define_path("XKEYSYMDB", os.path.join(self.package_folder, "share", "X11", "XKeysymDB"))
