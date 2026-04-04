import os
import shutil

from conan import ConanFile
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import NMakeToolchain, is_msvc

required_conan_version = ">=2.4"


class NASMConan(ConanFile):
    name = "nasm"
    package_type = "application"
    homepage = "http://www.nasm.us"
    description = "The Netwide Assembler, NASM, is an 80x86 and x86-64 assembler"
    license = "BSD-2-Clause"
    topics = ("asm", "installer", "assembler",)
    settings = "os", "arch", "compiler", "build_type"
    languages = ["C"]

    @property
    def _nasm(self):
        suffix = "w.exe" if is_msvc(self) else ""
        return os.path.join(self.package_folder, "bin", f"nasm{suffix}")

    @property
    def _ndisasm(self):
        suffix = "w.exe" if is_msvc(self) else ""
        return os.path.join(self.package_folder, "bin", f"ndisasm{suffix}")

    def _chmod_plus_x(self, filename):
        if os.name == "posix":
            os.chmod(filename, os.stat(filename).st_mode | 0o111)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            if not is_msvc(self):
                self.win_bash = True
                if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                    self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if is_msvc(self):
            tc = NMakeToolchain(self)
            tc.generate()
        else:
            tc = AutotoolsToolchain(self)
            tc.configure_args.append("--disable-werror")
            if self.settings.build_type == "Debug":
                tc.configure_args.append("--enable-debug")
            if self.settings.arch == "x86":
                tc.extra_cflags.append("-m32")
            elif self.settings.arch == "x86_64":
                tc.extra_cflags.append("-m64")
            # disable installation of man files
            tc.make_args.append("INSTALL_DATA=echo")
            tc.generate()

    def build(self):
        if is_msvc(self):
            with chdir(self, self.source_folder):
                self.run(r"nmake /f Mkfiles\msvc.mak")
        else:
            with chdir(self, self.source_folder):
                autotools = Autotools(self)
                autotools.configure()
                autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if is_msvc(self):
            copy(self, "*.exe", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
            with chdir(self, os.path.join(self.package_folder, "bin")):
                shutil.copy2("nasm.exe", "nasmw.exe")
                shutil.copy2("ndisasm.exe", "ndisasmw.exe")
        else:
            with chdir(self, self.source_folder):
                autotools = Autotools(self)
                autotools.install()
            rmdir(self, os.path.join(self.package_folder, "share"))
        self._chmod_plus_x(self._nasm)
        self._chmod_plus_x(self._ndisasm)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        compiler_executables = {"asm": self._nasm}
        self.conf_info.update("tools.build:compiler_executables", compiler_executables)
        self.buildenv_info.define_path("NASM", self._nasm)
        self.buildenv_info.define_path("NDISASM", self._ndisasm)
        self.buildenv_info.define_path("AS", self._nasm)
