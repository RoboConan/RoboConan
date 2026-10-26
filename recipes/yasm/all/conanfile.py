import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class YASMConan(ConanFile):
    name = "yasm"
    package_type = "application"
    homepage = "https://github.com/yasm/yasm"
    description = "Yasm is a complete rewrite of the NASM assembler under the 'new' BSD License"
    topics = ("yasm", "installer", "assembler")
    license = "BSD-2-Clause"
    settings = "os", "arch", "compiler", "build_type"
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        if is_msvc(self):
            cmake_layout(self, src_folder="src")
        else:
            basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler

    def build_requirements(self):
        if self.settings_build.os == "Windows" and not is_msvc(self):
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if "+git" in self.version and not is_msvc(self):
            self.tool_requires("autoconf/[^2.71]")
            self.tool_requires("automake/[^1.18.1]")
            self.tool_requires("libtool/[^2.4.7]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version][0], strip_root=True)
        apply_conandata_patches(self)
        # Don't call ./configure automatically
        if "+git" in self.version:
            replace_in_file(self, "autogen.sh", "$srcdir/configure", "# $srcdir/configure")

    def _generate_autotools(self):
        tc = AutotoolsToolchain(self)
        enable_debug = "yes" if self.settings.build_type == "Debug" else "no"
        tc.configure_args.extend([
            f"--enable-debug={enable_debug}",
            "--disable-rpath",
            "--disable-nls",
        ])
        if cross_building(self):
            build_cc = tc.vars().get("CC_FOR_BUILD", "cc")
            tc.configure_args.append(f"CC_FOR_BUILD={build_cc}")
            tc.configure_args.append(f"CCLD_FOR_BUILD={build_cc}")
        tc.generate()

    def _generate_cmake(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["YASM_BUILD_TESTS"] = False
        # Don't build shared libraries because:
        # 1. autotools doesn't build shared libs either
        # 2. the shared libs don't support static libc runtime (MT and such)
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["ENABLE_NLS"] = False
        tc.generate()

    def generate(self):
        if is_msvc(self):
            self._generate_cmake()
        else:
            self._generate_autotools()

    @staticmethod
    def _chmod_plus_x(name):
        os.chmod(name, os.stat(name).st_mode | 0o111)

    def build(self):
        if is_msvc(self):
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        else:
            with chdir(self, self.source_folder):
                autotools = Autotools(self)
                if "+git" in self.version:
                    self._chmod_plus_x("autogen.sh")
                    self._chmod_plus_x("YASM-VERSION-GEN.sh")
                    self.run("./autogen.sh")
                autotools.configure()
                autotools.make()

    def package(self):
        copy(self, "BSD.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if is_msvc(self):
            cmake = CMake(self)
            cmake.install()
        else:
            with chdir(self, self.source_folder):
                autotools = Autotools(self)
                autotools.install()
        rmdir(self, os.path.join(self.package_folder, "include"))
        rmdir(self, os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
