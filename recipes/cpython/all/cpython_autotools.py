import os
import textwrap

from conan import ConanFile
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.microsoft import *
from conan.tools.scm import Version


class CPythonAutotools(ConanFile):
    @property
    def _version_suffix(self):
        v = Version(self.version)
        return f"{v.major}.{v.minor}"

    @property
    def _abi_suffix(self):
        # https://github.com/python/cpython/blob/v3.13.5/configure.ac#L1728-L1766
        suffix = ""
        if self.options.get_safe("freethreaded"):
            suffix += "t"
        if self.settings.build_type == "Debug":
            suffix += "d"
        return suffix

    @property
    def _exact_lib_name(self):
        prefix = "" if self.settings.os == "Windows" else "lib"
        if self.settings.os == "Windows":
            extension = "lib"
        elif not self.options.shared:
            extension = "a"
        elif is_apple_os(self):
            extension = "dylib"
        else:
            extension = "so"
        return f"{prefix}{self._lib_name}.{extension}"

    def _autotools_build_requirements(self):
        if Version(self.version) >= "3.11" and not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def _autotools_validate(self):
        pass

    def _autotools_generate(self):
        VirtualRunEnv(self).generate(scope="build")

        tc = AutotoolsToolchain(self, prefix=self.package_folder)
        yes_no = lambda v: "yes" if v else "no"

        # Drop predefined static/shared configure flags
        tc.update_configure_args({
            "--enable-static": None,
            "--disable-static": None,
            "--enable-shared": None,
            "--disable-shared": None,
        })
        # Always build shared libraries for the interpreter and modules
        tc.configure_args.append("--enable-shared")
        # Also build static libs for shared=False
        tc.configure_args.append(f"--enable-static={yes_no(not self.options.shared)}")

        tc.configure_args += [
            f"--enable-optimizations={yes_no(self.options.pgo)}",
            f"--with-lto={yes_no(self.options.lto)}",
            f"--with-doc-strings={yes_no(self.options.docstrings)}",
            f"--with-pymalloc={yes_no(self.options.pymalloc)}",
            f"--with-pydebug={yes_no(self.settings.build_type == 'Debug')}",
            f"--with-readline={self.options.with_readline or 'no'}",
            "--with-system-expat",
            "--with-system-libmpdec",
        ]
        openssl_root = unix_path(self, self.dependencies["openssl"].package_folder)
        tc.configure_args.append(f"--with-openssl={openssl_root}")
        tc.configure_args.append("--disable-test-modules")
        if Version(self.version) >= "3.13" and self.options.freethreaded:
            tc.configure_args.append("--disable-gil")
        if Version(self.version) < "3.12":
            tc.configure_args.append("--with-system-ffi")
        if self.options.get_safe("with_sqlite3"):
            sqlite3_has_extensions = not self.dependencies["sqlite3"].options.omit_load_extension
            tc.configure_args.append(f"--enable-loadable-sqlite-extensions={yes_no(sqlite3_has_extensions)}")
        if self.options.get_safe("with_tkinter") and Version(self.version) < "3.11":
            tcltk_includes = []
            tcltk_libs = []
            for dep in ("tcl", "tk", "zlib"):
                cpp_info = self.dependencies[dep].cpp_info.aggregated_components()
                tcltk_includes += [f"-I{d}" for d in cpp_info.includedirs]
                tcltk_libs += [f"-L{lib}" for lib in cpp_info.libdirs]
                tcltk_libs += [f"-l{lib}" for lib in cpp_info.libs]
            if self.settings.os in ["Linux", "FreeBSD"] and not self.dependencies["tk"].options.shared:
                tcltk_libs.extend([f"-l{lib}" for lib in ("X11", "Xss")])
            tc.configure_args += [
                f"--with-tcltk-includes={' '.join(tcltk_includes)}",
                f"--with-tcltk-libs={' '.join(tcltk_libs)}",
            ]

        if not is_apple_os(self):
            tc.extra_ldflags.append("-Wl,--as-needed")

        if self.settings.os in ["Linux", "FreeBSD"]:
            # Add -lrt to fix _posixshmem.cpython-312-x86_64-linux-gnu.so: undefined symbol: shm_unlink
            tc.configure_args.append("POSIXSHMEM_LIBS=-lrt")

        if not can_run(self):
            build_python = unix_path(self, os.path.join(self.dependencies.build["cpython"].package_folder, "bin", "python"))
            tc.configure_args.append(f"--with-build-python={build_python}")
        # The following are required only when cross-building, but set for all cases for consistency
        tc.configure_args.append("--enable-ipv6")  # enabled by default, but skip the check
        dev_ptmx_exists = os.path.exists("/dev/ptmx")
        dev_ptc_exists = os.path.exists("/dev/ptc")
        tc.configure_args.append(f"ac_cv_file__dev_ptmx={yes_no(dev_ptmx_exists)}")
        tc.configure_args.append(f"ac_cv_file__dev_ptc={yes_no(dev_ptc_exists)}")

        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        if Version(self.version) >= "3.11":
            pkgdeps = PkgConfigDeps(self)
            pkgdeps.generate()

    def _patch_setup_py(self):
        setup_py = os.path.join(self.source_folder, "setup.py")

        def override_assignment(key, value):
            replace_in_file(self, setup_py, f"{key} = ", f"{key} = {repr(value)} #")

        if self.options.get_safe("with_curses"):
            libcurses = self.dependencies["ncurses"].cpp_info.components["libcurses"]
            tinfo = self.dependencies["ncurses"].cpp_info.components["tinfo"]
            curses_libs = libcurses.libs + libcurses.system_libs + tinfo.libs + tinfo.system_libs
        else:
            curses_libs = []
        override_assignment("curses_libs", curses_libs)

        if Version(self.version) < "3.11":
            openssl = self.dependencies["openssl"].cpp_info.aggregated_components()
            zlib = self.dependencies["zlib-ng"].cpp_info.aggregated_components()
            override_assignment("openssl_includes", openssl.includedirs + zlib.includedirs)
            override_assignment("openssl_libdirs", openssl.libdirs + zlib.libdirs)
            override_assignment("openssl_libs", openssl.libs + zlib.libs)

        if Version(self.version) < "3.11":
            replace_in_file(self, setup_py, "if (MACOS and self.detect_tkinter_darwin())", "if (False)")

    def _autotools_patch_sources(self):
        # <=3.10 requires a lot of manual injection of dependencies through setup.py
        # 3.12 removes setup.py completely, and uses pkgconfig dependencies
        # 3.11 is an in awkward transition state where some dependencies use pkgconfig, and others use setup.py
        if Version(self.version) < "3.12":
            self._patch_setup_py()

        if Version(self.version) >= "3.11":
            replace_in_file(self, os.path.join(self.source_folder, "configure"),
                            'OPENSSL_LIBS="-lssl -lcrypto"',
                            'OPENSSL_LIBS="-lssl -lcrypto -lz"')

        if Version(self.version) < "3.12":
            replace_in_file(self, os.path.join(self.source_folder, "Makefile.pre.in"),
                            "$(RUNSHARED) CC='$(CC)' LDSHARED='$(BLDSHARED)' OPT='$(OPT)'",
                            "$(RUNSHARED) CC='$(CC) $(CONFIGURE_CFLAGS) $(CONFIGURE_CPPFLAGS)' LDSHARED='$(BLDSHARED)' OPT='$(OPT)'")

        configure_path = os.path.join(self.source_folder, "configure")

        # ensure disabled dependencies are not autodetected
        def _disable_dep(var, opt):
            if not self.options.get_safe(f"with_{opt}"):
                replace_in_file(self, configure_path, f"{var}=yes", f"{var}=no")

        if Version(self.version) >= "3.13":
            _disable_dep("have_bzip2", "bz2")
            _disable_dep("have_curses", "curses")
            _disable_dep("have_panel", "curses")
            _disable_dep("have_gdbm", "gdbm")
            _disable_dep("have_liblzma", "lzma")
            _disable_dep("have_sqlite3", "sqlite3")
            _disable_dep("have_tcltk", "tkinter")
        if Version(self.version, qualifier=True) >= "3.14":
            _disable_dep("have_libzstd", "zstd")

    def _autotools_build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    @property
    def _cpython_symlink(self):
        symlink = os.path.join(self.package_folder, "bin", "python")
        if self.settings.os == "Windows":
            symlink += ".exe"
        return symlink

    def _autotools_package(self):
        autotools = Autotools(self)
        target = "sharedinstall" if is_apple_os(self) else "install"
        autotools.install(target=target, args=["DESTDIR="])
        if not self.options.shared:
            copy(self, self._exact_lib_name, self.build_folder, os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

        # Rewrite shebangs of python scripts
        for filename in os.listdir(os.path.join(self.package_folder, "bin")):
            filepath = os.path.join(self.package_folder, "bin", filename)
            if not os.path.isfile(filepath):
                continue
            if os.path.islink(filepath):
                continue
            with open(filepath, "rb") as fn:
                firstline = fn.readline(1024)
                if not(firstline.startswith(b"#!") and b"/python" in firstline and b"/bin/sh" not in firstline):
                    continue
                text = fn.read()
            self.output.info(f"Rewriting shebang of {filename}")
            with open(filepath, "wb") as fn:
                fn.write(textwrap.dedent(f"""\
                    #!/bin/sh
                    ''':'
                    __file__="$0"
                    while [ -L "$__file__" ]; do
                        __file__="$(dirname "$__file__")/$(readlink "$__file__")"
                    done
                    exec "$(dirname "$__file__")/python{self._version_suffix}" "$0" "$@"
                    '''
                    """).encode())
                fn.write(text)

        if not os.path.exists(self._cpython_symlink):
            os.symlink(f"python{self._version_suffix}", self._cpython_symlink)
        fix_apple_shared_install_name(self)

        # Remove the Stable ABI python3 library, matching the behavior of other major package managers.
        # As of v3.14 it does not contain any symbols and cannot be meaningfully linked against.
        # See https://github.com/python/cpython/issues/104612
        if Version(self.version) >= "3.12" and self.settings.os != "Windows":
            ext = ".dylib" if is_apple_os(self) else ".so"
            sabi_libname = f"libpython3{self._abi_suffix}{ext}"
            rm(self, sabi_libname, os.path.join(self.package_folder, "lib"))

        # Create symlinks of python3-config in a separate subdir from the interpreter to safely include it in the buildenv $PATH
        mkdir(self, os.path.join(self.package_folder, "bin", "config"))
        with chdir(self, os.path.join(self.package_folder, "bin", "config")):
            os.symlink(f"../python{self._version_suffix}-config", f"python{self._version_suffix}-config")
            os.symlink(f"../python{self._version_suffix}-config", "python3-config")
        # Pop an extra directory from the prefix path when inside bin/config.
        replace_in_file(self, os.path.join(self.package_folder, "bin", f"python{self._version_suffix}-config"),
                        "    echo $RESULT",
                        '    [ "$(basename "$RESULT")" = "bin" ] && RESULT=$(dirname "$RESULT")\n'
                        "    echo $RESULT")
