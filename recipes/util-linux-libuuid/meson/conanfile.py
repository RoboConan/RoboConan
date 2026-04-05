import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class UtilLinuxLibuuidConan(ConanFile):
    name = "util-linux-libuuid"
    description = "Universally unique id library"
    homepage = "https://github.com/util-linux/util-linux.git"
    license = "BSD-3-Clause"
    topics = "id", "identifier", "unique", "uuid"
    package_type = "library"
    provides = "libuuid"
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
        if self.settings.os == "Macos":
            # Required because libintl.{a,dylib} is not distributed via libc on Macos
            self.requires("gettext/[>=0.21 <1]")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on Windows")

    def build_requirements(self):
        self.tool_requires("bison/[^3.8.2]")
        self.tool_requires("flex/[^2.6.4]")
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "disabled"
        tc.project_options["build-libuuid"] = "enabled"
        # Enable libutil for older versions of glibc which still provide an actual libutil library.
        tc.project_options["libutil"] = "enabled"
        tc.project_options["program-tests"] = False
        # if "x86" in self.settings.arch:
        #     tc.c_args.append("-mstackrealign")
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING.BSD-3-Clause", os.path.join(self.source_folder, "Documentation", "licenses"), os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "sbin"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "usr"))
        # util-linux always builds both the shared and static libraries of libuuid, so delete the one that isn't needed.
        shared_library_extension = ".so"
        if self.settings.os == "Macos":
            shared_library_extension = ".dylib"
        rm(self, "libuuid.a" if self.options.shared else f"libuuid{shared_library_extension}*", os.path.join(self.package_folder, "lib"))
        rm(self, "*.a" if self.options.shared else f"*{shared_library_extension}*", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "uuid")
        self.cpp_info.set_property("cmake_target_name", "libuuid::libuuid")
        self.cpp_info.set_property("cmake_file_name", "libuuid")
        # Maintain alias to `LibUUID::LibUUID` for previous version of the recipe
        self.cpp_info.set_property("cmake_target_aliases", ["LibUUID::LibUUID"])

        self.cpp_info.libs = ["uuid"]
        self.cpp_info.includedirs.append(os.path.join("include", "uuid"))
