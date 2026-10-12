import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class LinuxPamConan(ConanFile):
    name = "linux-pam"
    description = "Pluggable Authentication Modules for Linux"
    license = "BSD-3-Clause"
    homepage = "https://github.com/linux-pam/linux-pam"
    topics = ("pam", "pluggable-authentication-module", "authentication", "security")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "with_db": ["db", "gdbm", False],
        "with_nis": [True, False],
        "with_openssl": [True, False],
        "with_selinux": [True, False],
        "with_systemd": [True, False],
        # TODO:
        # "with_audit": [True, False],
        # "with_econf": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "with_db": "gdbm",
        "with_nis": False,
        "with_openssl": True,
        "with_selinux": True,
        "with_systemd": True,
    }
    options_description = {
        "i18n": "Enable internationalization support",
        "with_db": "Build pam_userdb module with specified database backend",
        "with_nis": "Enable NIS/YP support in pam_unix using libnsl",
        "with_openssl": "Use OpenSSL crypto libraries in pam_timestamp",
        "with_selinux": "Enable SELinux support",
        "with_systemd": "Enable logind support in pam_issue and pam_timestamp",
    }
    languages = ["C"]
    implements = ["auto_shared_fpic"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_db == "db":
            self.requires("libdb/[^5.3.28]")
        elif self.options.with_db == "gdbm":
            self.requires("gdbm/1.23")
        if self.options.i18n and self.settings.os != "Linux":
            self.requires("gettext/[>=0.21 <1]")
        if self.options.with_openssl:
            self.requires("openssl/[<5]")
        if self.options.with_selinux:
            self.requires("libselinux/3.6")
        if self.options.with_systemd:
            self.requires("libsystemd/[^255]")

    def validate(self):
        if is_apple_os(self) or self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported.")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        feature = lambda option: "enabled" if option else "disabled"

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["docs"] = "disabled"
        tc.project_options["examples"] = "false"
        tc.project_options["xtests"] = "false"
        tc.project_options["audit"] = feature(self.options.get_safe("with_audit"))
        tc.project_options["econf"] = feature(self.options.get_safe("with_econf"))
        tc.project_options["i18n"] = feature(self.options.i18n)
        tc.project_options["logind"] = feature(self.options.with_systemd)
        tc.project_options["nis"] = feature(self.options.with_nis)
        tc.project_options["openssl"] = feature(self.options.with_openssl)
        tc.project_options["selinux"] = feature(self.options.with_selinux)
        tc.project_options["pam_userdb"] = feature(self.options.with_db)
        tc.project_options["db"] = str(self.options.with_db) if self.options.with_db else "auto"
        # Override auto value
        tc.project_options["pam_unix"] = "enabled"

        # To help find_library() calls in Meson
        if self.options.with_db:
            db_pkg = "libdb" if self.options.with_db == "db" else "gdbm"
            db = self.dependencies[db_pkg].cpp_info.aggregated_components()
            tc.extra_cflags.append('-I' + db.includedir)
            tc.extra_ldflags.append('-L' + db.libdir)

        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def _patch_sources(self):
        if not self.options.i18n:
            replace_in_file(self, os.path.join(self.source_folder, "libpam", "meson.build"), ", libintl", "")

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
        rm(self, "*.pdb", self.package_folder, recursive=True)
        fix_apple_shared_install_name(self)
        rmdir(self, os.path.join(self.package_folder, "var"))

    def package_info(self):
        self.cpp_info.components["pam"].set_property("pkg_config_name", "pam")
        self.cpp_info.components["pam"].libs = ["pam"]
        self.cpp_info.components["pam"].libdirs.append(os.path.join("lib", "security"))
        self.cpp_info.components["pam"].resdirs = ["etc", "lib/systemd"]
        if self.options.i18n:
            self.cpp_info.components["pam"].resdirs.append("share")
            if self.settings.os != "Linux":
                self.cpp_info.components["pam"].requires.append("gettext::gettext")

        self.cpp_info.components["pamc"].set_property("pkg_config_name", "pamc")
        self.cpp_info.components["pamc"].libs = ["pamc"]

        self.cpp_info.components["pam_misc"].set_property("pkg_config_name", "pam_misc")
        self.cpp_info.components["pam_misc"].libs = ["pam_misc"]
        self.cpp_info.components["pam_misc"].requires = ["pam"]

        # Most of the dependencies are used by the modules in lib/security/
        requires = ["pam"]
        if self.options.with_db == "db":
            requires.append("libdb::libdb")
        elif self.options.with_db == "gdbm":
            requires.append("gdbm::gdbm")
        if self.options.with_openssl:
            requires.append("openssl::openssl")
        if self.options.with_selinux:
            requires.append("libselinux::libselinux")
        if self.options.with_systemd:
            requires.append("libsystemd::libsystemd")
        self.cpp_info.components["_modules"].requires = requires
