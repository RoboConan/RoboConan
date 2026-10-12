import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, AutotoolsDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class LldpdConan(ConanFile):
    name = "lldpd"
    description = "lldpd: implementation of IEEE 802.1ab (LLDP)"
    license = "ISC AND GPL-2.0 WITH Linux-syscall-note"
    homepage = "https://lldpd.github.io/"
    topics = ("network", "discovery", "lldp", "cdp", "lldpd")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "with_libbsd": [True, False],
        "with_libevent": [True, False],
        "with_libcap": [True, False],
        "with_snmp": [True, False],
        "with_xml": [True, False],
        "with_readline": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "with_libbsd": False,
        "with_libevent": False,
        "with_libcap": False,
        "with_snmp": False,
        "with_xml": False,
        "with_readline": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.tools:
            del self.options.with_snmp
            del self.options.with_xml
            del self.options.with_readline

    def requirements(self):
        if self.options.with_libbsd:
            self.requires("libbsd/[>=0.10.0 <1]")
        if self.options.tools:
            if self.options.with_libevent:
                self.requires("libevent/[^2.1.12]")
            if self.options.with_libcap:
                self.requires("libcap/[^2.69]")
            if self.options.with_snmp:
                self.requires("net-snmp/[^5.9.4]", options={"enable_agent": True})
            if self.options.with_xml:
                self.requires("libxml2/[^2.12.5]")
            if self.options.with_readline:
                self.requires("readline/[^8.2]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")

        tc = AutotoolsToolchain(self)
        def yes_no(v): return "yes" if v else "no"
        tc.configure_args.extend([
            f"--with-libbsd={yes_no(self.options.with_libbsd)}",
            f"--with-snmp={yes_no(self.options.get_safe('with_snmp'))}",
            f"--with-xml={yes_no(self.options.get_safe('with_xml'))}",
            f"--with-readline={yes_no(self.options.get_safe('with_readline'))}",
            "--without-seccomp",
            "--disable-doxygen-doc",
        ])
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        if self.options.get_safe("with_snmp"):
            deps = AutotoolsDeps(self)
            deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        if not self.options.tools:
            rmdir(self, os.path.join(self.package_folder, "bin"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "etc"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.components["lldpctl"].set_property("pkg_config_name", "lldpctl")
        self.cpp_info.components["lldpctl"].libs = ["lldpctl"]
        if self.options.with_libbsd:
            self.cpp_info.components["lldpctl"].requires.append("libbsd::libbsd")

        if self.options.tools:
            tool_requires = []
            if self.options.with_libevent:
                tool_requires.append("libevent::libevent")
            if self.options.with_libcap:
                tool_requires.append("libcap::libcap")
            if self.options.with_snmp:
                tool_requires.append("net-snmp::net-snmp")
            if self.options.with_xml:
                tool_requires.append("libxml2::libxml2")
            if self.options.with_readline:
                tool_requires.append("readline::readline")
            self.cpp_info.components["_tools"].requires = tool_requires
