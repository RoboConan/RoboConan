import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class GPGErrorConan(ConanFile):
    name = "libgpg-error"
    description = "Libgpg-error is a small library that originally defined common error values for all GnuPG components."
    license = "GPL-2.0-or-later"
    homepage = "https://gnupg.org/software/libgpg-error/index.html"
    topics = ("gpg", "gnupg", "encrypt", "pgp", "openpgp")
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

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("This recipe only support Linux. You can contribute Windows and/or Macos support.")

    def build_requirements(self):
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-nls" if self.options.i18n else "--disable-nls",
            "--disable-dependency-tracking",
            "--disable-languages",
            "--disable-doc",
            "--disable-tests",
        ])
        if self.options.get_safe("fPIC", True):
            tc.configure_args.append("--with-pic")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*la", os.path.join(self.package_folder, "lib"))

    def finalize(self):
        copy(self, "*", src=self.immutable_package_folder, dst=self.package_folder)
        # Fix .pc so gpgrt-config reports correct paths
        pc_file = os.path.join(self.package_folder, "lib", "pkgconfig", "gpg-error.pc")
        replace_in_file(self, pc_file, "prefix=/", f"prefix={self.package_folder}")
        replace_in_file(self, pc_file, "Cflags: \n", "Cflags: -I${includedir}\n")

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "gpg-error")
        self.cpp_info.libs = ["gpg-error"]
        self.cpp_info.resdirs = ["share"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread"]
        aclocal_path = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.append_path("ACLOCAL_PATH", aclocal_path)
        # for gpgrt-config
        bin_path = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bin_path)
