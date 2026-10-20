import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class GdbmConan(ConanFile):
    name = "gdbm"
    description = (
        "gdbm is a library of database functions that uses extensible hashing and work similar to the standard UNIX dbm. "
        "These routines are provided to a programmer needing to create and manipulate a hashed database."
    )
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org.ua/software/gdbm/gdbm.html"
    topics = ("dbm", "hash", "database")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "libgdbm_compat": [True, False],
        "gdbmtool_debug": [True, False],
        "with_libiconv": [True, False],
        "with_readline": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "libgdbm_compat": False,
        "gdbmtool_debug": True,
        "with_libiconv": False,
        "with_readline": False,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")
        if not self.options.i18n:
            self.options.rm_safe("with_libiconv")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("with_libiconv"):
            self.requires("libiconv/[^1.17]")
        if self.options.with_readline:
            self.requires("readline/[^8.1.2]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.name} is not supported on Windows")

    def build_requirements(self):
        self.tool_requires("bison/[^3.8.2]")
        self.tool_requires("flex/[^2.6.4]")
        self.tool_requires("gnu-config/[*]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            venv = VirtualRunEnv(self)
            venv.generate(scope="build")
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        enable_debug = self.settings.build_type in ["Debug", "RelWithDebInfo"]
        tc.configure_args.extend([
            f"--enable-debug={yes_no(enable_debug)}",
            f"--enable-libgdbm-compat={yes_no(self.options.libgdbm_compat)}",
            f"--enable-gdbmtool-debug={yes_no(self.options.gdbmtool_debug)}",
            f"--enable-nls={yes_no(self.options.i18n)}",
            f"--with-readline={yes_no(self.options.with_readline)}",
            f"--with-pic={yes_no(self.options.get_safe('fPIC', True))}",
        ])
        if self.options.gdbmtool_debug:
            tc.extra_defines.append("YYDEBUG=1")
        if self.options.get_safe("with_libiconv"):
            libiconv_package_folder = self.dependencies.direct_host["libiconv"].package_folder
            tc.configure_args.extend([
                f"--with-libiconv-prefix={libiconv_package_folder}",
                "--with-libintl-prefix"
            ])
        else:
            tc.configure_args.extend([
                "--without-libiconv-prefix",
                "--without-libintl-prefix"
            ])
        if is_apple_os(self):
            # Inject -headerpad_max_install_names, otherwise fix_apple_shared_install_name() may fail.
            # See https://github.com/conan-io/conan-center-index/issues/20002
            tc.extra_ldflags.append("-headerpad_max_install_names")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def _patch_sources(self):
        for gnu_config in [
            self.conf.get("user.gnu-config:config_guess", check_type=str),
            self.conf.get("user.gnu-config:config_sub", check_type=str),
        ]:
            if gnu_config:
                copy(self, os.path.basename(gnu_config), os.path.dirname(gnu_config), os.path.join(self.source_folder, "build-aux"))

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(target="maintainer-clean-generic")
        autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        if self.options.libgdbm_compat:
            self.cpp_info.libs.append("gdbm_compat")
        self.cpp_info.libs.append("gdbm")
