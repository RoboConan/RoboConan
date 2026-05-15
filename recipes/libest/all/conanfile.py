import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class LibEstConan(ConanFile):
    name = "libest"
    description = "EST is used for secure certificate enrollment"
    license = "BSD-3-Clause"
    homepage = "https://github.com/cisco/libest"
    topics = ("EST", "RFC 7030", "certificate enrollment")

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

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.settings.os == "Windows" or is_apple_os(self):
            raise ConanInvalidConfiguration("Platform is currently not supported by this recipe")
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/1.1.1w", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "Makefile.in",
                        "@ENABLE_CLIENT_ONLY_FALSE@SUBDIRS = safe_c_stub src java/jni example/client example/client-simple example/server example/proxy example/client-brski",
                        "@ENABLE_CLIENT_ONLY_FALSE@SUBDIRS = safe_c_stub src")
        replace_in_file(self, "Makefile.in",
                        "@ENABLE_CLIENT_ONLY_TRUE@SUBDIRS = safe_c_stub src java/jni example/client example/client-simple example/client-brski",
                        "@ENABLE_CLIENT_ONLY_TRUE@SUBDIRS = safe_c_stub src")

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")
        tc = AutotoolsToolchain(self)
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "*LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            if self.settings.build_type in ["Release", "MinSizeRel"]:
                # https://github.com/cisco/libest/blob/r3.2.0/intro.txt#L244-L254
                autotools.install(target="install-strip")
            else:
                autotools.install()
        os.unlink(os.path.join(self.package_folder, "lib", "libest.la"))

    def package_info(self):
        self.cpp_info.libs = ["est"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["dl", "pthread"]
