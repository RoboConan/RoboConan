import os
import shutil

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibXMLPlusPlus(ConanFile):
    name = "libxmlpp"
    description = "libxml++ (a.k.a. libxmlplusplus) provides a C++ interface to XML files"
    license = "LGPL-2.1"
    homepage = "https://github.com/libxmlplusplus/libxmlplusplus"
    topics = ("xml", "parser", "wrapper")
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

    python_requires = "conan-utils/latest"

    @property
    def _lib_version(self):
        return "5.0"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libxml2/[^2.12.5]")
        self.requires("glibmm/2.75.0")

    def validate(self):
        check_min_cppstd(self, "17" if Version(self.version) >= "5.4.0" else "11")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _patch_sources(self):
        if is_msvc(self):
            # when using cpp_std=c++NM the /permissive- flag is added which
            # attempts enforcing standard conformant c++ code. the problem is
            # that older versions of the Windows SDK isn't standard conformant!
            # see:
            # https://developercommunity.visualstudio.com/t/error-c2760-in-combaseapih-with-windows-sdk-81-and/185399
            replace_in_file(self,
                os.path.join(self.source_folder, "meson.build"),
                "cpp_std=c++", "cpp_std=vc++")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["build-examples"] = "false"
        tc.project_options["build-tests"] = "false"
        tc.project_options["build-documentation"] = "false"
        tc.project_options["msvc14x-parallel-installable"] = "false"
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()

        shutil.move(
            os.path.join(self.package_folder, "lib", f"libxml++-{self._lib_version}", "include", "libxml++config.h"),
            os.path.join(self.package_folder, "include", f"libxml++-{self._lib_version}", "libxml++config.h"))

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", f"libxml++-{self._lib_version}"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

        if is_msvc(self):
            rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
            if not self.options.shared:
                rename(
                    self,
                    os.path.join(self.package_folder, "lib", f"libxml++-{self._lib_version}.a"),
                    os.path.join(self.package_folder, "lib", f"xml++-{self._lib_version}.lib"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", f"libxml++-{self._lib_version}")
        self.cpp_info.libs = [f"xml++-{self._lib_version}"]
        self.cpp_info.includedirs = [os.path.join("include", f"libxml++-{self._lib_version}")]
