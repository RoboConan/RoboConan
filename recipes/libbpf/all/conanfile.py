import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import Autotools, PkgConfigDeps, GnuToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"

class LibbpfConan(ConanFile):
    name = "libbpf"
    description = "eBPF helper library"
    license = "BSD-2-Clause OR LGPL-2.1-only"
    homepage = "https://github.com/libbpf/libbpf"
    topics = ("berkeley-packet-filter", "bpf", "ebpf", "network", "tracing")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_uapi_headers": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_uapi_headers": False
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("linux-headers-generic/[^6.5]", transitive_headers=True)
        self.requires("elfutils/[>=0.191 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("zlib-ng/[^2.0]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.ref} is only available on Linux")

    def build_requirements(self):
        self.tool_requires("make/[^4.4.1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        tc_vars = tc.extra_env.vars(self)
        tc.make_args["PREFIX"] = "/"
        tc.make_args["DESTDIR"] = self.package_folder
        tc.make_args["LIBSUBDIR"] = "lib"
        if not self.options.shared:
            tc.make_args["BUILD_STATIC_ONLY"] = 1
        tc.make_args["CC"] = tc_vars["CC"]
        tc.generate()

        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

    def build(self):
        with chdir(self, os.path.join(self.source_folder, "src")):
            autotools = Autotools(self)
            autotools.make()
            if self.options.with_uapi_headers:
                autotools.make('install_uapi_headers')

    def package(self):
        copy(self, pattern="LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        with chdir(self, os.path.join(self.source_folder, "src")):
            autotools = Autotools(self)
            autotools.install()

        if self.options.shared:
            rm(self, "libbpf.a", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "libbpf.so*", os.path.join(self.package_folder, "lib"))

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["bpf"]
        self.cpp_info.set_property("pkg_config_name", "libbpf")
