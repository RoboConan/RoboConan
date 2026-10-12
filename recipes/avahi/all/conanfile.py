import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class AvahiConan(ConanFile):
    name = "avahi"
    description = "Avahi - Service Discovery for Linux using mDNS/DNS-SD -- compatible with Bonjour"
    topics = ("bonjour", "dns", "dns-sd", "mdns")
    homepage = "https://github.com/lathiat/avahi"
    license = "LGPL-2.1-only"
    # --enable-compat-libdns_sd means that this recipe provides the mdnsresponder compile interface
    provides = "mdnsresponder"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]")
        self.requires("expat/[>=2.6.2 <3]")
        self.requires("libdaemon/0.14")
        self.requires("dbus/[^1.15]")
        self.requires("gdbm/1.23")
        self.requires("libevent/[^2.1.12]")
        self.requires("libcap/[^2.69]")

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            raise ConanInvalidConfiguration(f"{self.ref} only supports Linux.")

    def build_requirements(self):
        self.tool_requires("glib/<host_version>")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        virtual_build_env = VirtualBuildEnv(self)
        virtual_build_env.generate()
        if can_run(self):
            VirtualRunEnv(self).generate(scope="build")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-compat-libdns_sd")
        tc.configure_args.append("--enable-introspection=no")
        tc.configure_args.append("--disable-gtk3")
        tc.configure_args.append("--disable-mono")
        tc.configure_args.append("--disable-monodoc")
        tc.configure_args.append("--disable-python")
        tc.configure_args.append("--disable-qt5")
        tc.configure_args.append("--with-systemdsystemunitdir=/lib/systemd/system")
        tc.configure_args.append("--with-distro=none")
        tc.configure_args.append("--enable-nls" if self.options.i18n else "--disable-nls")
        tc.configure_args.append("ac_cv_func_strlcpy=no")
        tc.configure_args.append("ac_cv_func_setproctitle=no")
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        # Override Avahi's problematic check for the pkg-config executable.
        env = Environment()
        env.define("have_pkg_config", "yes")
        env.vars(self).save_script("conanbuild_pkg_config")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "etc"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "run"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        for lib in ("client", "common", "core", "glib", "gobject", "libevent", "compat-libdns_sd"):
            avahi_lib = f"avahi-{lib}"
            self.cpp_info.components[lib].set_property("pkg_config_name", avahi_lib)
            self.cpp_info.components[lib].libs = [avahi_lib]
            if lib != "common":
                self.cpp_info.components[lib].includedirs = ["include", os.path.join("include", avahi_lib)]
        self.cpp_info.components["compat-libdns_sd"].libs = ["dns_sd"]

        self.cpp_info.components["client"].requires = ["common", "dbus::dbus"]
        self.cpp_info.components["common"].system_libs = ["pthread"]
        self.cpp_info.components["core"].requires = ["common"]
        self.cpp_info.components["glib"].requires = ["common", "glib::glib"]
        self.cpp_info.components["gobject"].requires = ["client", "glib"]
        self.cpp_info.components["libevent"].requires = ["common", "libevent::libevent"]
        self.cpp_info.components["compat-libdns_sd"].requires = ["client"]

        for app in ("autoipd", "browse", "daemon", "dnsconfd", "publish", "resolve", "set-host-name"):
            avahi_app = f"avahi-{app}"
            self.cpp_info.components[app].set_property("pkg_config_name", avahi_app)

        self.cpp_info.components["autoipd"].requires = ["libdaemon::libdaemon"]
        self.cpp_info.components["browse"].requires = ["client", "gdbm::gdbm"]
        self.cpp_info.components["daemon"].requires = ["core", "expat::expat", "libdaemon::libdaemon", "libcap::libcap"]
        self.cpp_info.components["dnsconfd"].requires = ["common", "libdaemon::libdaemon"]
        self.cpp_info.components["publish"].requires = ["client"]
        self.cpp_info.components["resolve"].requires = ["client"]
        self.cpp_info.components["set-host-name"].requires = ["client"]
