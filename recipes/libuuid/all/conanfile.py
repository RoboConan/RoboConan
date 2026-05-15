import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class LibuuidConan(ConanFile):
    name = "libuuid"
    description = "Portable uuid C library"
    homepage = "https://sourceforge.net/projects/libuuid/"
    license = "BSD-3-Clause"
    topics = "id", "identifier", "unique", "uuid"
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

    @property
    def _has_sys_file_header(self):
        return self.settings.os in ["FreeBSD", "Linux", "Macos"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on Windows")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "configure",
            "sys/socket.h sys/time.h unistd.h",
            "sys/socket.h sys/syscall.h sys/time.h unistd.h")
        apply_conandata_patches(self)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        tc = AutotoolsToolchain(self)
        if self._has_sys_file_header:
            tc.extra_defines.append("HAVE_SYS_FILE_H")
        if "x86" in self.settings.arch:
            tc.extra_cflags.append("-mstackrealign")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "uuid")
        self.cpp_info.libs = ["uuid"]
        self.cpp_info.includedirs.append("include/uuid")
