import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building, check_max_cppstd
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class ResiprocateConan(ConanFile):
    name = "resiprocate"
    description = (
        "The project is dedicated to maintaining a complete, correct, "
        "and commercially usable implementation of SIP and a few related protocols."
    )
    license = "VSL-1.0"
    homepage = "https://github.com/resiprocate/resiprocate/wiki/"
    topics = ("sip", "voip", "communication", "signaling")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
        "with_postgresql": [True, False],
        "with_mysql": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": True,
        "with_postgresql": False,
        "with_mysql": False,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_ssl:
            self.requires("openssl/1.1.1w")  # OpenSSL 3.x is not supported
        if self.options.with_postgresql:
            self.requires("libpq/[^17.0]")
        if self.options.with_mysql:
            self.requires("libmysqlclient/[^8.1.0]")

    def validate(self):
        if self.settings.os == "Windows" or is_apple_os(self):
            # FIXME: unreleased versions of resiprocate use CMake and should support Windows and macOS
            raise ConanInvalidConfiguration(f"reSIProcate recipe does not currently support {self.settings.os}.")
        # Uses deprecated std::allocator<void>::const_pointer, which has been removed in C++20
        check_max_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("libtool/[^2.4.7]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            venv = VirtualRunEnv(self)
            venv.generate(scope="build")
        tc = AutotoolsToolchain(self)
        # These options do not support yes/no
        if self.options.with_ssl:
            tc.configure_args.append("--with-ssl")
        if self.options.with_mysql:
            tc.configure_args.append("--with-mysql")
        if self.options.with_postgresql:
            tc.configure_args.append("--with-postgresql")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.autoreconf()
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.la", os.path.join(self.package_folder), recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["resip", "rutil", "dum", "resipares"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
