import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class DbusConan(ConanFile):
    name = "dbus"
    # license is AFL-2.1 OR GPL-2.0-or-later with several other compatible licenses for smaller sections of code
    license = "(AFL-2.1 OR GPL-2.0-or-later) AND DocumentRef-COPYING"
    homepage = "https://www.freedesktop.org/wiki/Software/dbus"
    description = "D-Bus is a simple system for interprocess communication and coordination."
    topics = "bus", "interprocess", "message"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "dbus_user": [None, "ANY"],
        "message_bus": [True, False],
        "system_socket": [None, "ANY"],
        "system_pid_file": [None, "ANY"],
        "session_socket_dir": [None, "ANY"],
        "with_x11": [True, False],
        "with_systemd": [True, False],
        "with_selinux": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "dbus_user": "messagebus",
        "message_bus": False,
        "system_socket": "/run/dbus/system_bus_socket",  # default on Ubuntu
        "system_pid_file": None,
        "session_socket_dir": "/tmp",
        "with_x11": False,
        "with_systemd": False,
        "with_selinux": False,
    }
    options_description = {
        "dbus_user": "User for running the system dbus-daemon. Default is 'messagebus'.",
        "message_bus": "Enable dbus-daemon",
        "system_socket": "Path for the UNIX domain socket for systemwide daemon",
        "system_pid_file": "PID file path for systemwide daemon",
        "session_socket_dir": "Where to put sockets for the per-login-session message bus.",
        "with_x11": "Build with X11 auto-launch support",
        "with_systemd": "Enable Systemd at_console support",
        "with_selinux": "Enable SELinux support.",
    }
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_systemd
            del self.options.with_x11
            del self.options.with_selinux
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.message_bus:
            self.options.rm_safe("dbus_user")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("expat/[>=2.6.2 <3]")
        if self.options.get_safe("with_systemd"):
            self.requires("libsystemd/[^255]")
        if self.options.get_safe("with_selinux"):
            self.requires("libselinux/3.6")
        if self.options.get_safe("with_x11"):
            # X11 is only linked into an executable and should not be propagated as a library dependency.
            # It should still be provided in a VirtualRunEnv context, though,
            # but Conan as of v2.2 does not yet provide a fine-grained enough control over this.
            self.requires("xorg/system", visible=False)

    def package_id(self):
        # The dbus_user option only effects the installation of dbus during the package method.
        # Otherwise, it only appears in the system.conf file in the package.
        self.info.options.rm_safe("dbus_user")

    def validate(self):
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < 7:
            raise ConanInvalidConfiguration(f"{self.ref} requires at least gcc 7.")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config",check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["asserts"] = not is_apple_os(self)
        tc.project_options["checks"] = False
        tc.project_options["doxygen_docs"] = "disabled"
        tc.project_options["ducktype_docs"] = "disabled"
        tc.project_options["qt_help"] = "disabled"
        tc.project_options["modular_tests"] = "disabled"
        tc.project_options["selinux"] = "enabled" if self.options.get_safe("with_selinux") else "disabled"
        if self.options.session_socket_dir:
            tc.project_options["session_socket_dir"] = str(self.options.session_socket_dir)
        tc.project_options["systemd"] = "enabled" if self.options.get_safe("with_systemd") else "disabled"
        tc.project_options["message_bus"] = bool(self.options.message_bus)
        if self.options.get_safe("dbus_user"):
            tc.project_options["dbus_user"] = str(self.options.dbus_user)
        if self.options.system_pid_file:
            tc.project_options["system_pid_file"] = str(self.options.system_pid_file)
        if self.options.system_socket:
            tc.project_options["system_socket"] = str(self.options.system_socket)
        tc.project_options["x11_autolaunch"] = "enabled" if self.options.get_safe("with_x11") else "disabled"
        tc.project_options["xml_docs"] = "disabled"
        # explicitly disable auto features
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["apparmor"] = "disabled"
        tc.project_options["kqueue"] = "disabled"
        tc.project_options["launchd"] = "disabled"
        tc.project_options["libaudit"] = "disabled"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def _patch_sources(self):
        replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                        "subdir('test')", "# subdir('test')")

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "LICENSES"), os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()

        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))

        # rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "DBus1")
        self.cpp_info.set_property("cmake_target_name", "dbus-1")
        self.cpp_info.set_property("pkg_config_name", "dbus-1")
        self.cpp_info.libs = ["dbus-1"]
        self.cpp_info.includedirs.extend([
            os.path.join("include", "dbus-1.0"),
            os.path.join("lib", "dbus-1.0", "include"),
        ])
        self.cpp_info.resdirs = ["share", "etc"]
        if is_apple_os(self):
            self.cpp_info.resdirs.append("LaunchAgents")
        if self.settings.os == "Linux":
            self.cpp_info.system_libs.append("rt")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.extend(["iphlpapi", "ws2_32"])
        else:
            self.cpp_info.system_libs.append("pthread")

        if not self.options.shared:
            self.cpp_info.defines.append("DBUS_STATIC_BUILD")

        self.cpp_info.requires.append("expat::expat")
        if self.options.get_safe("with_systemd"):
            self.cpp_info.requires.append("libsystemd::libsystemd")
        if self.options.get_safe("with_selinux"):
            self.cpp_info.requires.append("libselinux::selinux")

        self.cpp_info.set_property("pkg_config_custom_content", textwrap.dedent("""\
            datarootdir=/usr/share
            datadir=${datarootdir}
            sysconfdir=/etc
            system_bus_default_address=unix:path=%s
            session_bus_services_dir=/usr/share/dbus-1/services
            system_bus_services_dir=/usr/share/dbus-1/system-services
            interfaces_dir=/usr/share/dbus-1/interfaces
            daemondir=/usr/bin
        """ % self.options.system_socket))
