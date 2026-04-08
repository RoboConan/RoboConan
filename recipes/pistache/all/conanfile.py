import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class PistacheConan(ConanFile):
    name = "pistache"
    description = "Pistache is a modern and elegant HTTP and REST framework for C++"
    license = "Apache-2.0"
    homepage = "https://github.com/pistacheio/pistache"
    topics = ("http", "rest", "framework", "networking")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
        "with_libevent": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": False,
        "with_libevent": False
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    @property
    def _supports_libevent(self):
        return Version(self.version) >= "0.4.25"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux" or not self._supports_libevent:
            del self.options.with_libevent

    def requirements(self):
        self.requires("rapidjson/[>=0.0+git.20250205]")
        self.requires("date/[^3.0]")
        if self.options.with_ssl:
            self.requires("openssl/[>=1.1 <4]")
        if self.settings.os != "Linux" or self.options.get_safe("with_libevent"):
            # INFO: meson.build:188: Linux can use native epoll support. Other OS need libevent always
            self.requires("libevent/[^2.1.12]")

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD"] and Version(self.version) < "0.4.25":
            raise ConanInvalidConfiguration(f"{self.ref} is only support on Linux.")

        if self.settings.compiler == "clang" and Version(self.version) < "0.4.25":
            raise ConanInvalidConfiguration(f"{self.ref}'s clang support is broken. See pistacheio/pistache#835.")

        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["PISTACHE_USE_SSL"] = bool(self.options.with_ssl)
        tc.project_options["PISTACHE_BUILD_EXAMPLES"] = False
        tc.project_options["PISTACHE_BUILD_TESTS"] = False
        tc.project_options["PISTACHE_BUILD_DOCS"] = False
        if self.settings.os == "Linux" and self._supports_libevent:
            tc.project_options["PISTACHE_FORCE_LIBEVENT"] = bool(self.options.with_libevent)
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.set_property("rapidjson", "pkg_config_name", "RapidJSON")
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libpistache")
        self.cpp_info.libs = ["pistache"]
        if self.options.with_ssl:
            self.cpp_info.defines = ["PISTACHE_USE_SSL=1"]
        self.cpp_info.cflags = ["-pthread"]
        self.cpp_info.system_libs = ["m"]
