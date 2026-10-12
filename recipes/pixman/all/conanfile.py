import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.4"


class PixmanConan(ConanFile):
    name = "pixman"
    description = "Pixman is a low-level software library for pixel manipulation"
    topics = ("graphics", "compositing", "rasterization")
    homepage = "https://gitlab.freedesktop.org/pixman/pixman"
    license = "MIT"
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

    python_requires = "conan-utils/latest"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "meson.build", "subdir('test')", "")
        replace_in_file(self, "meson.build", "subdir('demos')", "")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["tests"] = "disabled"
        tc.project_options["demos"] = "disabled"
        tc.project_options["libpng"] = "disabled"
        tc.project_options["gtk"] = "disabled"
        tc.project_options["openmp"] = "disabled"

        # Android armv7 build of Pixman makes use of cpu-features functionality, provided in the NDK
        if self.settings.os == "Android":
            android_ndk_home = self.conf.get("tools.android:ndk_path")
            cpu_features_path = os.path.join(android_ndk_home, "sources", "android", "cpufeatures").replace("\\", "/")
            tc.project_options["cpu-features-path"] = cpu_features_path

        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        lib_folder = os.path.join(self.package_folder, "lib")
        rmdir(self, os.path.join(lib_folder, "pkgconfig"))
        rm(self, "*.la", lib_folder)
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.libs = ['libpixman-1'] if self.settings.os == "Windows" and not self.options.shared else ['pixman-1']
        self.cpp_info.includedirs.append(os.path.join("include", "pixman-1"))
        self.cpp_info.set_property("pkg_config_name", "pixman-1")
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["pthread", "m"]
