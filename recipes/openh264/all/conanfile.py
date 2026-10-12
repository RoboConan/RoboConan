import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import stdcpp_library
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class OpenH264Conan(ConanFile):
    name = "openh264"
    description = "Open Source H.264 Codec"
    license = "BSD-2-Clause"
    homepage = "http://www.openh264.org/"
    topics = ("h264", "codec", "video", "compression", )
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
    def _is_clang_cl(self):
        return self.settings.os == 'Windows' and self.settings.compiler == 'clang'

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if self.settings.arch in ["x86", "x86_64"]:
            self.tool_requires("nasm/[*]")
        if is_msvc(self) and self.settings.arch == "armv8":
            self.tool_requires("strawberryperl/[*]")
            self.tool_requires("gas-preprocessor/[*]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["tests"] = "disabled"
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        meson = Meson(self)
        meson.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        if is_msvc(self) or self._is_clang_cl:
            rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
            if not self.options.shared:
                rename(self, os.path.join(self.package_folder, "lib", "libopenh264.a"),
                        os.path.join(self.package_folder, "lib", "openh264.lib"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.libs = [f"openh264"]
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs.extend(["m", "pthread"])
        if self.settings.os == "Android":
            self.cpp_info.system_libs.append("m")
        if not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                if self.settings.os == "Android" and libcxx == "c++_static":
                    # INFO: When builing for Android, need to link against c++abi too. Otherwise will get linkage errors:
                    # ld.lld: error: undefined symbol: operator new(unsigned long)
                    # >>> referenced by welsEncoderExt.cpp
                    self.cpp_info.system_libs.append("c++abi")
                self.cpp_info.system_libs.append(libcxx)
