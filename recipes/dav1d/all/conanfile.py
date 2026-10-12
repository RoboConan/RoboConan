import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class Dav1dConan(ConanFile):
    name = "dav1d"
    description = "dav1d is a new AV1 cross-platform decoder, open-source, and focused on speed, size and correctness."
    homepage = "https://www.videolan.org/projects/dav1d.html"
    topics = ("av1", "codec", "video", "decoding")
    license = "BSD-2-Clause"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "bit_depth": ["all", 8, 16],
        "tools": [True, False],
        "assembly": [True, False],
        "with_xxhash": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "bit_depth": "all",
        "tools": True,
        "assembly": True,
        "with_xxhash": True,
    }

    python_requires = "conan-utils/latest"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if is_msvc(self) and self.settings.build_type == "Debug":
            # debug builds with assembly often causes linker hangs or LNK1000
            self.options.assembly = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_xxhash:
            self.requires("xxhash/[>=0.8.1 <0.9]", libs=False)

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if self.options.assembly and self.settings.arch in ["x86", "x86_64"]:
            self.tool_requires("nasm/[*]")
        if is_msvc(self) and self.settings.arch == "armv8":
            self.tool_requires("gas-preprocessor/[*]")
            self.tool_requires("strawberryperl/[*]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "meson.build", "subdir('doc')", "")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["enable_tests"] = False
        tc.project_options["enable_asm"] = self.options.assembly
        tc.project_options["enable_tools"] = self.options.tools
        if self.options.bit_depth == "all":
            tc.project_options["bitdepths"] = "8,16"
        else:
            tc.project_options["bitdepths"] = str(self.options.bit_depth)
        tc.project_options["xxhash_muxer"] = "enabled" if self.options.with_xxhash else "disabled"
        if self.options.with_xxhash:
            tc.extra_cflags.append(f"-I{self.dependencies['xxhash'].cpp_info.includedir}")
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "dav1d")
        self.cpp_info.libs = ["dav1d"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["dl", "pthread"])
