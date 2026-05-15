import os

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class Krb5Conan(ConanFile):
    name = "krb5"
    description = "Kerberos is a network authentication protocol. It is designed to provide strong authentication " \
                  "for client/server applications by using secret-key cryptography."
    homepage = "https://web.mit.edu/kerberos"
    topics = ("kerberos", "network", "authentication", "protocol", "client", "server", "cryptography")
    license = "DocumentRef-NOTICE:LicenseRef-"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "i18n": [True, False],
        "use_thread": [True, False],
        "use_dns_realms": [True, False],
        "with_tls": [False, "openssl"],
    }
    default_options = {
        "i18n": False,
        "use_thread": True,
        "use_dns_realms": False,
        "with_tls": "openssl"
    }
    options_description = {
        "i18n": "Enable internationalization support",
        "use_thread": "Enable thread support",
        "use_dns_realms": "Enable DNS for realms",
        "with_tls": "Enable TLS support with OpenSSL",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libverto/[>=0.3.2 <1]")
        if self.options.with_tls == "openssl":
            self.requires("openssl/[>=1.1 <4]")
        if self.options.get_safe("with_tcl"):
            self.requires("tcl/[^8.6.16]")

    def build_requirements(self):
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        self.tool_requires("bison/[^3.8.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "src/Makefile.in",
            "\tkdc kadmin kprop clients appl tests ",
            "\tkdc kadmin kprop clients appl ")
        replace_in_file(self, "src/config/pre.in",
            "INSTALL_SETUID=$(INSTALL) $(INSTALL_STRIP) -m 4755 -o root",
            "INSTALL_SETUID=$(INSTALL) $(INSTALL_STRIP) -m 755")
        replace_in_file(self, "src/configure",
            '    TLS_IMPL_LIBS="-lssl -lcrypto"',
            '    TLS_IMPL_LIBS=$(pkg-config --libs openssl 2>/dev/null)')

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        tls_impl = {"openssl": "openssl",}.get(str(self.options.with_tls))
        tc.configure_args.extend([
            f"--enable-thread-support={yes_no(self.options.get_safe('use_thread'))}",
            f"--enable-dns-for-realm={yes_no(self.options.use_dns_realms)}",
            f"--enable-pkinit={yes_no(self.options.with_tls)}",
            f"--with-crypto-impl={(tls_impl or 'builtin')}",
            f"--with-spake-openssl={yes_no(self.options.with_tls == 'openssl')}",
            f"--with-tls-impl={(tls_impl or 'no')}",
            f"--enable-nls={yes_no(self.options.i18n)}",
            "--disable-rpath",
            "--without-libedit",
            "--without-readline",
            "--with-system-verto",
            "--enable-dns-for-realm",
            f"--with-keyutils={self.package_folder}",
            f"--with-tcl={(self.dependencies['tcl'].package_folder if self.options.get_safe('with_tcl') else 'no')}",
            ])
        if not can_run(self):
            # Use values from Linux GCC as a guess for try_compile checks.
            tc.configure_args.extend([
                "krb5_cv_attr_constructor_destructor=yes,yes",
                "ac_cv_func_regcomp=yes",
                "ac_cv_printf_positional=yes",
            ])
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) >= 15:
            # GCC 15 makes strchr/strstr type-generic (const-preserving); suppress -Werror=discarded-qualifiers
            # by pre-setting WARN_CFLAGS so configure skips its extra warning flag injection
            tc.configure_args.append("WARN_CFLAGS=")
        tc.generate()

        pkg = AutotoolsDeps(self)
        pkg.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure(build_script_folder="src")
        autotools.make()

    def package(self):
        copy(self, "NOTICE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "examples"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "var"))

    def package_info(self):
        self.cpp_info.components["mit-krb5"].set_property("pkg_config_name", "mit-krb5")
        self.cpp_info.components["mit-krb5"].libs = ["krb5", "k5crypto", "com_err", "krb5support"]
        self.cpp_info.components["mit-krb5"].requires = ["libverto::libverto"]
        if self.options.with_tls == "openssl":
            self.cpp_info.components["mit-krb5"].requires.append("openssl::openssl")
        if self.settings.os == "Linux":
            self.cpp_info.components["mit-krb5"].system_libs = ["resolv"]

        self.cpp_info.components["libkrb5"].set_property("pkg_config_name", "krb5")
        self.cpp_info.components["libkrb5"].requires = ["mit-krb5"]

        self.cpp_info.components["mit-krb5-gssapi"].set_property("pkg_config_name", "mit-krb5-gssapi")
        self.cpp_info.components["mit-krb5-gssapi"].libs = ["gssapi_krb5"]
        self.cpp_info.components["mit-krb5-gssapi"].requires = ["mit-krb5"]

        self.cpp_info.components["krb5-gssapi"].set_property("pkg_config_name", "krb5-gssapi")
        self.cpp_info.components["krb5-gssapi"].requires = ["mit-krb5-gssapi"]

        self.cpp_info.components["gssrpc"].set_property("pkg_config_name", "gssrpc")
        self.cpp_info.components["gssrpc"].libs = ["gssrpc"]
        self.cpp_info.components["gssrpc"].requires = ["mit-krb5-gssapi"]

        self.cpp_info.components["kadm-client"].set_property("pkg_config_name", "kadm-client")
        self.cpp_info.components["kadm-client"].libs = ["kadm5clnt_mit"]
        self.cpp_info.components["kadm-client"].requires = ["mit-krb5-gssapi", "gssrpc"]

        self.cpp_info.components["kdb"].set_property("pkg_config_name", "kdb")
        self.cpp_info.components["kdb"].libs = ["kdb5"]
        self.cpp_info.components["kdb"].requires = ["mit-krb5-gssapi", "mit-krb5", "gssrpc"]

        self.cpp_info.components["kadm-server"].set_property("pkg_config_name", "kadm-server")
        self.cpp_info.components["kadm-server"].libs = ["kadm5srv_mit"]
        self.cpp_info.components["kadm-server"].requires = ["kdb", "mit-krb5-gssapi"]

        self.cpp_info.components["krad"].libs = ["krad"]
        self.cpp_info.components["krad"].requires = ["libkrb5"]

        krb5_config = os.path.join(self.package_folder, "bin", "krb5-config").replace("\\", "/")
        self.output.info(f"Appending KRB5_CONFIG environment variable: {krb5_config}")
        self.runenv_info.define_path("KRB5_CONFIG", krb5_config)
