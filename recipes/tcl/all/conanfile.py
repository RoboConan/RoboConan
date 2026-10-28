import os
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime, msvc_runtime_flag, NMakeToolchain, NMakeDeps
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class TclConan(ConanFile):
    name = "tcl"
    description = "Tcl is a very powerful but easy to learn dynamic programming language."
    license = "TCL"
    homepage = "https://tcl.tk"
    topics = ("scripting", "programming")
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

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")
        # source folder must be a sub-directory of the build folder
        self.folders.build = "."

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        self.requires("libtommath/[^1.3]")
        self.requires("sqlite3/[^3.40]")

    def validate(self):
        if self.settings.os not in ("FreeBSD", "Linux", "Macos", "Windows"):
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on {self.settings.os}.")

    def build_requirements(self):
        if self.settings_build.os == "Windows" and not is_msvc(self):
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # unvendor most of zlib
        for path in Path("compat/zlib").iterdir():
            if path.is_file() and path.name not in {"zutil.h", "crc32.h"}:
                path.unlink()
        # unvendor libtommath and sqlite3 while retaining Tcl's sqlite extension
        rmdir(self, os.path.join(self.source_folder, "libtommath"))
        sqlite = next(Path(self.source_folder, "pkgs").glob("sqlite*"))
        for path in (sqlite / "compat" / "sqlite3").iterdir():
            if path.name != "spaceanal.tcl":
                path.unlink()

        unix_config_dir = os.path.join(self.source_folder, "unix")
        unix_makefile_in = os.path.join(unix_config_dir, "Makefile.in")

        # Avoid clearing CFLAGS and LDFLAGS in the makefile
        replace_in_file(self, unix_makefile_in, "\nCFLAGS\t", "\n#CFLAGS\t")
        replace_in_file(self, unix_makefile_in, "\nLDFLAGS\t", "\n#LDFLAGS\t")
        # Use CFLAGS and CPPFLAGS as argument to CC
        replace_in_file(self, unix_makefile_in, "${CFLAGS}", "${CFLAGS} ${CPPFLAGS}")

        win_config_dir = os.path.join(self.source_folder, "win")

        # Fix install for MinGW
        win_makefile_in = os.path.join(win_config_dir, "Makefile.in")
        replace_in_file(self, win_makefile_in, "INSTALL_ROOT	=", "INSTALL_ROOT	= $(DESTDIR)")
        # No link to static libgcc for MinGW
        win_tcl_m4 = os.path.join(win_config_dir, "tcl.m4")
        replace_in_file(self, win_tcl_m4, "-static-libgcc", "")

    def generate(self):
        if is_msvc(self):
            tc = NMakeToolchain(self)
            tc.generate()
            deps = NMakeDeps(self)
            deps.generate()
        else:
            if not cross_building(self):
                env = VirtualRunEnv(self)
                env.generate(scope="build")

            tc = AutotoolsToolchain(self)
            def yes_no(v): return "yes" if v else "no"
            # Tcl's configure script does not use the standard Autotools static
            # switches.  Static/shared selection is inferred from --enable-shared.
            tc.update_configure_args({
                "--enable-static": None,
                "--disable-static": None,
            })
            tc.configure_args.extend([
                # Embedding the script library in a static archive does not make
                # it available to arbitrary consumers linked against that archive.
                "--disable-zipfs",
                "--with-system-libtommath",
                "PKG_CFG_ARGS=--with-system-sqlite",
                f"--enable-symbols={yes_no(self.settings.build_type == 'Debug')}",
                f"--enable-64bit={yes_no(self.settings.arch == 'x86_64')}",
            ])
            if self.settings.os in ["Linux", "FreeBSD"]:
                # Ensure the library has a soname, fix https://github.com/conan-io/conan-center-index/issues/27691
                # (mirror debian behavior)
                tc.configure_args.append("TCL_SHLIB_LD_EXTRAS=-Wl,-soname,${TCL_LIB_FILE}")
            tc.generate()

            deps = AutotoolsDeps(self)
            deps.generate()

    def _patch_sources(self):
        if is_apple_os(self) and self.settings.arch not in ("x86", "x86_64"):
            macos_configure = os.path.join(self.source_folder, "macosx", "configure")
            replace_in_file(self, macos_configure, "#define HAVE_CPUID 1", "#undef HAVE_CPUID")

    def _build_nmake(self, targets):
        opts = ["noembed"]
        # https://core.tcl.tk/tips/doc/trunk/tip/477.md
        if not self.options.shared:
            opts.append("static")
        if self.settings.build_type == "Debug":
            opts.append("symbols")
        if is_msvc_static_runtime(self):
            opts.append("nomsvcrt")
        else:
            opts.append("msvcrt")
        if "d" not in msvc_runtime_flag(self):
            opts.append("unchecked")

        with chdir(self, os.path.join(self.source_folder, "win")):
            opts = ",".join(opts)
            targets = " ".join(targets)
            self.run(f'nmake -nologo -f makefile.vc INSTALLDIR="{self.package_folder}" OPTS={opts} {targets}')

    def _get_configure_subdir(self):
        return {
            "Macos": "macosx",
            "Linux": "unix",
            "FreeBSD": "unix",
            "Windows": "win",
        }[str(self.settings.os)]

    def build(self):
        self._patch_sources()
        if is_msvc(self):
            self._build_nmake(["release"])
        else:
            autotools = Autotools(self)
            autotools.configure(build_script_folder=self._get_configure_subdir())
            # https://core.tcl.tk/tcl/tktview/840660e5a1
            for root, _, list_of_files in os.walk(self.build_folder):
                if "Makefile" in list_of_files:
                    replace_in_file(self, os.path.join(root, "Makefile"), "-Dstrtod=fixstrtod", "", strict=False)
            # For some reason this target "binaries" may not be built before others
            # on Windows while it's a dependency of many other targets
            autotools.make(target="binaries")
            autotools.make()

    def package(self):
        copy(self, "license.terms", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if is_msvc(self):
            self._build_nmake(["install-binaries", "install-libraries", "install-pkgs"])
        else:
            autotools = Autotools(self)
            autotools.install()
            autotools.install(target="install-private-headers")
            rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
            rmdir(self, os.path.join(self.package_folder, "man"))
            rmdir(self, os.path.join(self.package_folder, "share"))
            fix_apple_shared_install_name(self)
        # Relocatable tclConfig.sh
        self._fix_tcl_config()

    def _fix_tcl_config(self):
        tcl_config = os.path.join(self.package_folder, "lib", "tclConfig.sh")
        ## Comment out references to build folder
        replace_in_file(self, tcl_config, "\nTCL_BUILD_", "\n#TCL_BUILD_")
        replace_in_file(self, tcl_config, "\nTCL_SRC_DIR", "\n#TCL_SRC_DIR")
        ## Replace references to package folder by TCL_ROOT env var supposed to be defined by VirtualRunEnv
        if is_msvc(self):
            replace_in_file(self, tcl_config, self.package_folder.replace("/", "\\"), "${TCL_ROOT}")
            zlib_lib = self.dependencies["zlib-ng"].cpp_info.libs[0]
            replace_in_file(self, tcl_config, "TCL_ZLIB_LIB_NAME='zdll.lib'",
                            f"TCL_ZLIB_LIB_NAME='{zlib_lib}.lib'")
            content = load(self, tcl_config)
            content = re.sub(r" -Fp[^ ]+", "", content)
            content = re.sub(r' -I"[^"]+\\(?:win|generic)"', "", content)
            content = content.replace(" /DBUILD_tcl", "")
            save(self, tcl_config, content)
        else:
            replace_in_file(self, tcl_config, "TCL_PREFIX='/'", "TCL_PREFIX='${TCL_ROOT}'")
            replace_in_file(self, tcl_config, "TCL_EXEC_PREFIX='/'", "TCL_EXEC_PREFIX='${TCL_ROOT}'")
            for to_replace in ["//", "/"]:
                replace_in_file(self, tcl_config, f"-L{to_replace}lib", "-L${TCL_ROOT}/lib", strict=False)
                replace_in_file(self, tcl_config, f"{{{to_replace}lib}}", "{${TCL_ROOT}/lib}", strict=False)
                replace_in_file(self, tcl_config, f"='{to_replace}lib", "='${TCL_ROOT}/lib", strict=False)
                replace_in_file(self, tcl_config, f"-I{to_replace}include", "-I${TCL_ROOT}/include", strict=False)
            for dep in ["zlib-ng", "libtommath", "sqlite3"]:
                var = f"CONAN_TCL_{dep.upper().replace('-', '_')}_ROOT"
                replace_in_file(self, tcl_config, self.dependencies[dep].package_folder, "${%s}" % var)
            replace_in_file(self, tcl_config, "TCL_LIBS='",
                            "TCL_LIBS='-L${CONAN_TCL_SQLITE3_ROOT}/lib "
                            "-L${CONAN_TCL_LIBTOMMATH_ROOT}/lib "
                            "-L${CONAN_TCL_ZLIB_NG_ROOT}/lib ")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "TCL")
        self.cpp_info.set_property("pkg_config_name", "tcl")
        # Match the versioned pkg-config alias installed by upstream.
        v = Version(self.version)
        self.cpp_info.set_property("pkg_config_aliases", [f"tcl{v.major}.{v.minor}"])

        if is_msvc(self):
            suffix = "" if self.options.shared else "s"
            if not self.options.shared and is_msvc_static_runtime(self):
                suffix += "x"
            self.cpp_info.libs = [f"tcl{v.major}{v.minor}{suffix}", "tclstub"]
        else:
            self.cpp_info.libs = [f"tcl{v.major}.{v.minor}", "tclstub"]

        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "netapi32", "userenv"]
        elif self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
        elif is_apple_os(self):
            self.cpp_info.frameworks = ["CoreFoundation"]

        if is_msvc(self) and not self.options.shared:
            self.cpp_info.defines.append("STATIC_BUILD")
        self.cpp_info.defines.append("TCL_WITH_EXTERNAL_TOMMATH")

        tcl_library = os.path.join(self.package_folder, "lib", f"tcl{v.major}.{v.minor}")
        self.runenv_info.define_path("TCL_LIBRARY", tcl_library)

        self.runenv_info.define_path("TCL_ROOT", self.package_folder)

        for dep in ["zlib-ng", "libtommath", "sqlite3"]:
            var = f"CONAN_TCL_{dep.upper().replace('-', '_')}_ROOT"
            self.buildenv_info.define_path(var, self.dependencies[dep].package_folder)

        tclsh = str(next(Path(self.package_folder, "bin").glob("tclsh*")))
        self.runenv_info.define_path("TCLSH", tclsh)
