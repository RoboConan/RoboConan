import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class InihConan(ConanFile):
    name = "inih"
    description = "Simple .INI file parser in C, good for embedded systems "
    license = "BSD-3-Clause"
    topics = ("ini", "configuration", "parser")
    homepage = "https://github.com/benhoyt/inih"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_inireader": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_inireader": True,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-utils/latest"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # INIReader is written in C++
        if not self.options.with_inireader:
            self.settings.rm_safe("compiler.libcxx")
            self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # since 57, INIReader requires C++11
        if Version(self.version) >= "57" and self.options.with_inireader:
            check_min_cppstd(self, 11)
        if self.options.shared and is_msvc(self):
            raise ConanInvalidConfiguration("Shared inih is not supported with msvc")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["distro_install"] = True
        tc.project_options["with_INIReader"] = self.options.with_inireader
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "INIReader")

        self.cpp_info.components["libinih"].set_property("pkg_config_name", "inih")
        self.cpp_info.components["libinih"].libs = ["inih"]

        if self.options.with_inireader:
            self.cpp_info.components["inireader"].set_property("pkg_config_name", "INIReader")
            self.cpp_info.components["inireader"].libs = ["INIReader"]
            self.cpp_info.components["inireader"].requires = ["libinih"]
