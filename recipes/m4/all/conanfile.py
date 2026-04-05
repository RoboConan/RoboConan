import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class M4Conan(ConanFile):
    name = "m4"
    description = "GNU M4 is an implementation of the traditional Unix macro processor"
    license = "GPL-3.0-only"
    homepage = "https://www.gnu.org/software/m4/"
    package_type = "application"
    topics = ("macro", "preprocessor")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "i18n": [True, False],
    }
    default_options = {
        "i18n": False,
    }

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ar-lib", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # This requires linking to ssp on some systems, which might not always present.
        # If this is really desired:
        # * add `-lssp` to LDFLAGS, and
        # * add `-D_FORTIFY_SOURCE=2` to CPPFLAGS/CFLAGS
        replace_in_file(self, "lib/config.hin",
                        "#  define _FORTIFY_SOURCE 2",
                        "// #  define _FORTIFY_SOURCE 2")
        # Disable tests and examples
        save(self, "tests/Makefile.in", "all:;\ninstall:;\n")
        save(self, "examples/Makefile.in", "all:;\ninstall:;\n")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-nls" if self.options.i18n else "--disable-nls",
        ])
        if is_msvc(self):
            # Avoid a `Assertion Failed Dialog Box` during configure with build_type=Debug
            # Visual Studio does not support the %n format flag:
            # https://docs.microsoft.com/en-us/cpp/c-runtime-library/format-specification-syntax-printf-and-wprintf-functions
            # Because the %n format is inherently insecure, it is disabled by default. If %n is encountered in a format string,
            # the invalid parameter handler is invoked, as described in Parameter Validation. To enable %n support, see _set_printf_count_output.
            tc.configure_args.extend([
                "gl_cv_func_printf_directive_n=no",
                "gl_cv_func_snprintf_directive_n=no",
                "gl_cv_func_snprintf_directive_n=no",
            ])
            if self.settings.build_type in ("Debug", "RelWithDebInfo"):
                tc.extra_ldflags.append("-PDB")
        elif self.settings.compiler == "clang" and Version(self.version) < "1.4.19":
            tc.extra_cflags.extend([
                "-rtlib=compiler-rt",
                "-Wno-unused-command-line-argument",
            ])
        if cross_building(self) and is_msvc(self):
            triplet_arch_windows = {"x86_64": "x86_64", "x86": "i686", "armv8": "aarch64"}

            host_arch = triplet_arch_windows.get(str(self.settings.arch))
            build_arch = triplet_arch_windows.get(str(self.settings_build.arch))

            if host_arch and build_arch:
                host = f"{host_arch}-w64-mingw32"
                build = f"{build_arch}-w64-mingw32"
                tc.configure_args.extend([
                    f"--host={host}",
                    f"--build={build}",
                ])
        if self.settings.os == "Windows":
            tc.configure_args.append("ac_cv_func__set_invalid_parameter_handler=yes")
        env = tc.environment()
        # help2man trick
        env.prepend_path("PATH", self.source_folder)
        # handle msvc
        if is_msvc(self):
            ar_wrapper = unix_path(self, os.path.join(self.source_folder, "build-aux", "ar-lib"))
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("LD", "link")
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")
        tc.generate(env)

    def _patch_sources(self):
        if shutil.which("help2man") is None:
            # dummy file for configure
            help2man = os.path.join(self.source_folder, "help2man")
            save(self, help2man, "#!/usr/bin/env bash\n:")
            if os.name == "posix":
                os.chmod(help2man, os.stat(help2man).st_mode | 0o111)
        if self.settings_build.os == "Windows":
            # ar-lib is needed for building m4 with Visual Studio.
            # Re-use the one from m4/1.4.18.
            # We can't use automake here to avoid a build cycle (m4 -> automake -> autoconf -> m4)
            copy(self, "ar-lib", self.export_sources_folder, os.path.join(self.source_folder, "build-aux"))

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share", "info"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        if self.options.i18n:
            self.cpp_info.resdirs = ["share"]

        # M4 environment variable is used by a lot of scripts as a way to override a hard-coded embedded m4 path
        bin_ext = ".exe" if self.settings.os == "Windows" else ""
        m4_bin = os.path.join(self.package_folder, "bin", f"m4{bin_ext}").replace("\\", "/")
        self.runenv_info.define_path("M4", m4_bin)
        self.buildenv_info.define_path("M4", m4_bin)
