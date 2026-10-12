import os
import shutil
import textwrap
from pathlib import Path

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class ZlibRsConan(ConanFile):
    name = "zlib-rs"
    description = "A safer zlib - Rust implementation of the zlib file format that is compatible with the zlib API"
    license ="Zlib"
    homepage = "https://github.com/trifectatechfoundation/zlib-rs"
    topics = ("zlib", "rust", "compression")
    provides = "zlib"
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
    languages = ["C"]

    def config_options(self):
        # The library is always built as PIC
        del self.options.fPIC
        if self.settings.os == "Windows":
            # static builds don't work
            del self.options.shared
            self.package_type = "shared-library"

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("rust/[>=1.75 <2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["zlib-rs"], strip_root=True)
        download(self, **self.conan_data["sources"][self.version]["zlib.h"], filename="zlib.h")
        download(self, **self.conan_data["sources"][self.version]["zconf.h"], filename="zconf.h")
        download(self, **self.conan_data["sources"][self.version]["LICENSE-zlib"], filename="LICENSE-zlib")
        # Add a profile for RelWithDebInfo
        save(self, "Cargo.toml", content=textwrap.dedent("""\
            [profile.release-with-debug]
            inherits = "release"
            debug = true
        """), append=True)

    def generate(self):
        env = Environment()
        # Ensure the correct linker is used, especially when cross-compiling
        target_upper = self.conf.get("user.rust:target_host", check_type=str).upper().replace("-", "_")
        cc = AutotoolsToolchain(self).vars().get("CC")
        if cc:
            env.define_path(f"CARGO_TARGET_{target_upper}_LINKER", cc)
        # Don't add the Cargo dependencies to a global Cargo cache
        env.define_path("CARGO_HOME", os.path.join(self.build_folder, "cargo"))
        env.vars(self).save_script("cargo_paths")

    @property
    def _build_type_flag(self):
        if self.settings.build_type == "Debug":
            return ""
        elif self.settings.build_type == "RelWithDebInfo":
            return "--profile=release-with-debug"
        elif self.settings.build_type == "MinSizeRel":
            return "--profile=release-opt-size"
        return "--release"

    def build(self):
        self.run(f"cargo rustc {self._build_type_flag} --features gz --target-dir {self.build_folder}",
                 cwd=os.path.join(self.source_folder, "libz-rs-sys-cdylib"))

    @property
    def _dist_dir(self):
        build_type = "debug" if self.settings.build_type == "Debug" else "release"
        if cross_building(self):
            platform = self.conf.get("user.rust:target_host", check_type=str)
            return Path(self.build_folder, platform, build_type)
        return Path(self.build_folder, build_type)

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "zlib.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "zconf.h", self.source_folder, os.path.join(self.package_folder, "include"))
        library_suffixes = {".dll", ".dylib", ".lib", ".so"} if self.options.get_safe("shared", True) else {".a", ".lib"}
        # Using shutil since copy() copies unrelated junk
        for path in self._dist_dir.glob("*z_rs*.*"):
            if path.suffix not in library_suffixes:
                continue
            dest = Path(self.package_folder, "bin" if path.suffix == ".dll" else "lib")
            dest.mkdir(exist_ok=True)
            shutil.copy2(path, os.path.join(dest, path.name))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "ZLIB")
        self.cpp_info.set_property("cmake_target_name", "ZLIB::ZLIB")
        self.cpp_info.set_property("pkg_config_name", "zlib")
        self.cpp_info.set_property("system_package_version", "1.3.2")

        self.cpp_info.libs = ["z_rs"]
