import os
import shutil

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, NMakeToolchain

required_conan_version = ">=2.4"


class LibMP3LameConan(ConanFile):
    name = "libmp3lame"
    description = "LAME is a high quality MPEG Audio Layer III (MP3) encoder licensed under the LGPL."
    homepage = "http://lame.sourceforge.net"
    topics = "multimedia", "audio", "mp3", "decoder", "encoding", "decoding"
    license = "LGPL-2.0"

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

    @property
    def _is_clang_cl(self):
        return str(self.settings.compiler) in ["clang"] and str(self.settings.os) in ['Windows']

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        if not is_msvc(self) and not self._is_clang_cl:
            self.tool_requires("gnu-config/[*]")
            if self.settings_build.os == "Windows":
                self.win_bash = True
                if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                    self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if is_msvc(self) or self._is_clang_cl:
            tc = NMakeToolchain(self)
            tc.generate()
        else:
            env = VirtualBuildEnv(self)
            env.generate()
            tc = AutotoolsToolchain(self)
            tc.configure_args.append("--disable-frontend")
            tc.configure_args.append("--disable-decoder")
            if self.settings.compiler == "clang" and self.settings.arch in ["x86", "x86_64"]:
                tc.extra_cxxflags.extend(["-mmmx", "-msse"])
            tc.generate()

    def _build_vs(self):
        with chdir(self, self.source_folder):
            shutil.copy2("configMS.h", "config.h")
            # Honor vc runtime
            replace_in_file(self, "Makefile.MSVC", "CC_OPTS = $(CC_OPTS) /MT", "")
            # Do not hardcode LTO
            replace_in_file(self, "Makefile.MSVC", " /GL", "")
            replace_in_file(self, "Makefile.MSVC", " /LTCG", "")
            replace_in_file(self, "Makefile.MSVC", "ADDL_OBJ = bufferoverflowU.lib", "")
            command = "nmake -f Makefile.MSVC comp=msvc"
            if self._is_clang_cl:
                compilers_from_conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
                buildenv_vars = VirtualBuildEnv(self).vars()
                cl = compilers_from_conf.get("c", buildenv_vars.get("CC", "clang-cl"))
                link = buildenv_vars.get("LD", "lld-link")
                replace_in_file(self, "Makefile.MSVC", "CC = cl", f"CC = {cl}")
                replace_in_file(self, "Makefile.MSVC", "LN = link", f"LN = {link}")
                # what is /GAy? MSDN doesn't know it
                # clang-cl: error: no such file or directory: '/GAy'
                # https://docs.microsoft.com/en-us/cpp/build/reference/ga-optimize-for-windows-application?view=msvc-170
                replace_in_file(self, "Makefile.MSVC", "/GAy", "/GA")
            if self.settings.arch == "x86_64":
                replace_in_file(self, "Makefile.MSVC", "MACHINE = /machine:I386", "MACHINE =/machine:X64")
                command += " MSVCVER=Win64 asm=yes"
            elif self.settings.arch == "armv8":
                replace_in_file(self, "Makefile.MSVC", "MACHINE = /machine:I386", "MACHINE =/machine:ARM64")
                command += " MSVCVER=Win64"
            else:
                command += " asm=yes"
            command += " libmp3lame.dll" if self.options.shared else " libmp3lame-static.lib"
            self.run(command)

    def _build_autotools(self):
        for gnu_config in [
            self.conf.get("user.gnu-config:config_guess", check_type=str),
            self.conf.get("user.gnu-config:config_sub", check_type=str),
        ]:
            if gnu_config:
                copy(self, os.path.basename(gnu_config), src=os.path.dirname(gnu_config), dst=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def build(self):
        if is_msvc(self) or self._is_clang_cl:
            self._build_vs()
        else:
            self._build_autotools()

    def package(self):
        copy(self, pattern="LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder,"licenses"))
        if is_msvc(self) or self._is_clang_cl:
            copy(self, pattern="*.h", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder,"include", "lame"))
            name = "libmp3lame.lib" if self.options.shared else "libmp3lame-static.lib"
            copy(self, name, src=os.path.join(self.source_folder, "output"), dst=os.path.join(self.package_folder,"lib"))
            if self.options.shared:
                copy(self, pattern="*.dll", src=os.path.join(self.source_folder, "output"), dst=os.path.join(self.package_folder,"bin"))
            rename(self, os.path.join(self.package_folder, "lib", name),
                         os.path.join(self.package_folder, "lib", "mp3lame.lib"))
        else:
            autotools = Autotools(self)
            autotools.install()
            rmdir(self, os.path.join(self.package_folder, "share"))
            rm(self, "*.la", os.path.join(self.package_folder, "lib"))
            fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "lame")
        self.cpp_info.libs = ["mp3lame"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs.append(os.path.join("include", "lame"))
