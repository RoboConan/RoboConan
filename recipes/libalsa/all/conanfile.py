import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class LibalsaConan(ConanFile):
    name = "libalsa"
    description = "Library of ALSA: The Advanced Linux Sound Architecture, that provides audio " \
                  "and MIDI functionality to the Linux operating system"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/alsa-project/alsa-lib"
    topics = ("alsa", "sound", "audio", "midi")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "disable_python": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "disable_python": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration(f"{self.name} only supports Linux")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        tc.configure_args.extend([
            f"--enable-python={yes_no(not self.options.disable_python)}",
        ])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "ALSA")

        libalsa = self.cpp_info.components["libalsa"]
        libalsa.set_property("cmake_target_name", "ALSA::ALSA")
        libalsa.set_property("pkg_config_name", "alsa")
        libalsa.libs = ["asound"]
        libalsa.resdirs = ["share"]
        libalsa.system_libs = ["dl", "m", "rt", "pthread"]

        atopology = self.cpp_info.components["atopology"]
        atopology.set_property("cmake_target_name", "ALSA::atopology")
        atopology.set_property("pkg_config_name", "alsa-topology")
        atopology.libs = ["atopology"]
        atopology.requires = ["libalsa"]

        alsa_config_dir = os.path.join(self.package_folder, "share", "alsa")
        self.runenv_info.define_path("ALSA_CONFIG_DIR", alsa_config_dir)
        aclocal_dir = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.append_path("ACLOCAL_PATH", aclocal_dir)
