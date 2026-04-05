import os
import re
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class LibtoolConan(ConanFile):
    name = "libtool"
    description = "GNU libtool is a generic library support script. "
    license = "GPL-2.0-or-later AND LGPL-2.0-or-later"
    # most common use is as "application", but library traits
    # are a superset of application so this should cover all cases
    package_type = "library"
    homepage = "https://www.gnu.org/software/libtool/"
    topics = ("configure", "library", "shared", "static")
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

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("gnu-config/[*]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        else:
            self.tool_requires("automake/[^1.18.1]", visible=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "Makefile.in", "$(update_mans)", "# $(update_mans)")

    def generate(self):
        if is_msvc(self):
            # __VSCMD_ARG_NO_LOGO: this test_package has too many invocations,
            #                      this avoids printing the logo everywhere
            # VSCMD_SKIP_SENDTELEMETRY: avoid the telemetry process holding onto the directory
            #                           unnecessarily
            env = Environment()
            env.define("__VSCMD_ARG_NO_LOGO", "1")
            env.define("VSCMD_SKIP_SENDTELEMETRY", "1")
            env.vars(self, scope="build").save_script("conanbuild_vcvars_options")

        tc = AutotoolsToolchain(self)

        tc.configure_args.extend([
            "--enable-shared",
            "--enable-static",
            "--enable-ltdl-install",
        ])

        tc.make_args.append("V=1")
        tc.make_args.append("VERBOSE=1")

        env = tc.environment()
        if is_msvc(self):
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            env.define("NM", "dumpbin -symbols")

            # Disable Fortran detection to handle issue with VS 2022
            # See: https://savannah.gnu.org/patch/?9313#comment1
            # In the future this could be removed if a new version fixes this
            # upstream
            env.define("F77", "no")
            env.define("FC", "no")

            tc.configure_args.append('lt_cv_sys_global_symbol_pipe="MS dumpbin"')
        tc.generate(env)

    def _patch_sources(self):
        config_guess =  self.dependencies.build["gnu-config"].conf_info.get("user.gnu-config:config_guess")
        config_sub = self.dependencies.build["gnu-config"].conf_info.get("user.gnu-config:config_sub")
        shutil.copy(config_sub, os.path.join(self.source_folder, "build-aux", "config.sub"))
        shutil.copy(config_guess, os.path.join(self.source_folder, "build-aux", "config.guess"))

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    @property
    def _shared_ext(self):
        if self.settings.os == "Windows":
            return "dll"
        elif is_apple_os(self):
            return "dylib"
        else:
            return "so"

    @property
    def _static_ext(self):
        if is_msvc(self):
            return "lib"
        else:
            return "a"

    def _rm_binlib_files_containing(self, ext_inclusive, ext_exclusive=None):
        regex_in = re.compile(fr".*\.({ext_inclusive})($|\..*)")
        if ext_exclusive:
            regex_out = re.compile(fr".*\.({ext_exclusive})($|\..*)")
        else:
            regex_out = re.compile("^$")
        for directory in (
                os.path.join(self.package_folder, "bin"),
                os.path.join(self.package_folder, "lib"),
        ):
            for file in os.listdir(directory):
                if regex_in.match(file) and not regex_out.match(file):
                    os.unlink(os.path.join(directory, file))

    def package(self):
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        fix_apple_shared_install_name(self)

        rmdir(self, os.path.join(self.package_folder, "share", "info"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))

        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            self._rm_binlib_files_containing(self._static_ext, self._shared_ext)
        else:
            self._rm_binlib_files_containing(self._shared_ext)

        replaces = {
            "GREP": "/usr/bin/env grep",
            "EGREP": "/usr/bin/env grep -E",
            "FGREP": "/usr/bin/env grep -F",
            "SED": "/usr/bin/env sed",
        }
        for file in [
            Path(self.package_folder, "bin", "libtool"),
            Path(self.package_folder, "bin", "libtoolize"),
        ]:
            contents = file.read_text(encoding="utf-8")
            for key, repl in replaces.items():
                contents, nb1 = re.subn('^%s="[^"]*"' % key, '%s="%s"' % (key, repl), contents, flags=re.MULTILINE)
                contents, nb2 = re.subn(r'^: \$\{%s="[^$"]*"}' % key, ': ${%s="%s"}' % (key, repl), contents, flags=re.MULTILINE)
                if nb1 + nb2 == 0:
                    raise ConanException(f"Failed to find {key} in {repl}")
            file.write_text(contents, encoding="utf-8")

        binpath = os.path.join(self.package_folder, "bin")
        if self.settings.os == "Windows":
            rename(self, os.path.join(binpath, "libtoolize"),
                         os.path.join(binpath, "libtoolize.exe"))
            rename(self, os.path.join(binpath, "libtool"),
                         os.path.join(binpath, "libtool.exe"))

        if is_msvc(self) and self.options.shared:
            rename(self, os.path.join(self.package_folder, "lib", "ltdl.dll.lib"),
                         os.path.join(self.package_folder, "lib", "ltdl.lib"))

    def package_info(self):
        self.cpp_info.libs = ["ltdl"]

        if self.options.shared:
            if self.settings.os == "Windows":
                self.cpp_info.defines = ["LIBLTDL_DLL_IMPORT"]
        else:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs = ["dl"]

        # Define environment variables such that libtool m4 files are seen by Automake
        libtool_aclocal_dir = os.path.join(self.package_folder, "share", "aclocal")

        self.buildenv_info.append_path("ACLOCAL_PATH", libtool_aclocal_dir)
        self.runenv_info.append_path("ACLOCAL_PATH", libtool_aclocal_dir)
