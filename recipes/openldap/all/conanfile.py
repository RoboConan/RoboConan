import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, GnuToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class OpenldapConan(ConanFile):
    name = "openldap"
    description = "OpenLDAP C library"
    license = "OLDAP-2.8"
    homepage = "https://www.openldap.org/"
    topics = ("ldap", "load-balancer", "directory-access")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_cyrus_sasl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_cyrus_sasl": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/[<5]")
        if self.options.with_cyrus_sasl:
            self.requires("cyrus-sasl/[^2.1.28]")

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD", "Macos"]:
            raise ConanInvalidConfiguration(f"{self.name} is only supported on Unix platforms")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "configure", "\n\nsystemdsystemunitdir=", "\n\n")
        save(self, "doc/Makefile.in", "all:\ninstall:\n")

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        def yes_no(v):
            return "yes" if v else "no"

        tc = GnuToolchain(self)
        tc.configure_args["--with-cyrus_sasl"] = yes_no(self.options.with_cyrus_sasl)
        tc.configure_args["--with-fetch"] = "no"
        tc.configure_args["--with-tls"] = "openssl"
        tc.configure_args["--enable-auditlog"] = "yes"
        tc.configure_args["systemdsystemunitdir"] = os.path.join(self.package_folder, 'res')
        if cross_building(self):
            # When cross-building, yielding_select should be explicit:
            # https://git.openldap.org/openldap/openldap/-/blob/OPENLDAP_REL_ENG_2_5/configure.ac#L1636
            tc.configure_args["--with-yielding_select"] = "yes"
            # Workaround: https://bugs.openldap.org/show_bug.cgi?id=9228
            tc.configure_args["ac_cv_func_memcmp_working"] = "yes"
        tc.generate()
        tc = AutotoolsDeps(self)
        tc.generate()

    def build(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install()
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, "COPYRIGHT", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        rm(self, "*.la", self.package_folder, recursive=True)
        fix_apple_shared_install_name(self)
        for folder in ["var", "share", "etc", os.path.join("lib", "pkgconfig"), "home", "Users"]:
            rmdir(self, os.path.join(self.package_folder, folder))

    def package_info(self):
        self.cpp_info.components["ldap"].set_property("pkg_config_name", "ldap")
        self.cpp_info.components["ldap"].libs = ["ldap"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["ldap"].system_libs = ["pthread", "resolv"]
        self.cpp_info.components["ldap"].requires = ["lber", "openssl::ssl", "openssl::crypto"]
        if self.options.with_cyrus_sasl:
            self.cpp_info.components["ldap"].requires.append("cyrus-sasl::cyrus-sasl")

        self.cpp_info.components["lber"].set_property("pkg_config_name", "lber")
        self.cpp_info.components["lber"].libs = ["lber"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["lber"].system_libs = ["pthread"]
