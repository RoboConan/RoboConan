import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class LibgcryptConan(ConanFile):
    name = "libgcrypt"
    description = "Libgcrypt is a general purpose cryptographic library originally based on code from GnuPG"
    homepage = "https://www.gnupg.org/download/index.html#libgcrypt"
    license = "LGPL-2.1-or-later"
    topics = ("gcrypt", "gnupg", "gpg", "crypto", "cryptography")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libcap/[^2.69]")
        self.requires("libgpg-error/[^1.49]", transitive_headers=True)

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(
                "This recipe only support Linux. You can contribute Windows and/or Macos support."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        save(self, "tests/Makefile.in", "all:;\ninstall:;\n")

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-doc"])
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libgcrypt")
        self.cpp_info.libs = ["gcrypt"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread"]
        aclocal_path = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.append_path("ACLOCAL_PATH", aclocal_path)

        # FIXME: these are missing from .pc:
        # host=x86_64-pc-linux-gnu
        # api_version=1
        # symmetric_ciphers="arcfour blowfish cast5 des aes twofish serpent rfc2268 seed camellia idea salsa20 gost28147 chacha20 sm4 aria"
        # asymmetric_ciphers="dsa elgamal rsa ecc kyber dilithium"
        # digests="crc gostr3411-94  md4 md5 rmd160 sha1 sha256 sha512 sha3 tiger whirlpool stribog blake2 sm3"
