import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, rmdir, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.18.0"


class LibnetfilterLogConan(ConanFile):
    name = "libnetfilter_log"
    license = "GPL-2.0-or-later"
    description = "Library providing interface to packets that have been logged by the kernel packet filter"
    homepage = "https://netfilter.org/projects/libnetfilter_log/index.html"
    topics = ("networking", "linux", "nftables")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
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
        self.requires("libmnl/[^1.0.4]")
        self.requires("libnfnetlink/[^1.0.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            raise ConanInvalidConfiguration(f"{self.ref} is only supported on Linux and FreeBSD.")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "etc"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "none")
        self.cpp_info.components["log"].set_property("pkg_config_name", "libnetfilter_log")
        self.cpp_info.components["log"].libs = ["netfilter_log"]
        self.cpp_info.components["log"].requires = ["libnfnetlink::libnfnetlink", "libmnl::libmnl"]
        self.cpp_info.components["ipulog"].set_property("pkg_config_name", "libnetfilter_log_libipulog")
        self.cpp_info.components["ipulog"].libs = ["netfilter_log_libipulog"]
        self.cpp_info.components["ipulog"].requires = ["log", "libnfnetlink::libnfnetlink"]
