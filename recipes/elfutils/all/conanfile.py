import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools import CppInfo
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class ElfutilsConan(ConanFile):
    name = "elfutils"
    description = "A dwarf, dwfl and dwelf functions to read DWARF, find separate debuginfo, symbols and inspect process state."
    homepage = "https://sourceware.org/elfutils"
    topics = ("libelf", "libdw", "libasm")
    license = "LGPL-3.0-or-later OR GPL-2.0-or-later"  # the library, executables are GPL
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "debuginfod": [True, False],
        "libdebuginfod": [True, False],
        "with_bzlib": [True, False],
        "with_lzma": [True, False],
        "with_zstd": [True, False],
        "with_sqlite3": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "debuginfod": False,
        "libdebuginfod": False,
        "with_bzlib": True,
        "with_lzma": True,
        "with_zstd": True,
        "with_sqlite3": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC
        if Version(self.version) < "0.186":
            del self.options.libdebuginfod
            del self.options.with_zstd

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        if self.options.with_sqlite3:
            self.requires("sqlite3/[>=3.45.0 <4]")
        if self.options.with_bzlib:
            self.requires("bzip2/[^1.0.8]")
        if self.options.with_lzma:
            self.requires("xz_utils/[^5.4.5]")
        if self.options.get_safe("with_zstd"):
            self.requires("zstd/[~1.5]")
        if self.options.get_safe("libdebuginfod"):
            self.requires("libcurl/[>=7.78.0 <9]")
        if self.options.debuginfod:
            self.requires("libmicrohttpd/0.9.75")

    def build_requirements(self):
        self.tool_requires("automake/[^1.18.1]")
        self.tool_requires("m4/[^1.4.20]")
        self.tool_requires("flex/[^2.6.4]")
        self.tool_requires("bison/[^3.8.2]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def validate(self):
        # Note that elfutils cannot be built on macOS
        # Example Error: "configure: error: __thread support required"
        # Reference: https://stackoverflow.com/questions/72372589/elfutils-build-error-on-mac-configure-error-thread-support-required
        if self.settings.os == "Macos":
            raise ConanInvalidConfiguration("elfutils does not support macOS.")
        if self.settings.compiler in ["apple-clang", "msvc"]:
            raise ConanInvalidConfiguration(f"Your compiler {self.settings.compiler} is not supported. "
                                            "elfutils only supports GCC and Clang.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-werror",
            "--enable-static={}".format("no" if self.options.shared else "yes"),
            "--enable-deterministic-archives",
            "--enable-silent-rules",
            "--with-zlib",
            "--with-bzlib" if self.options.with_bzlib else "--without-bzlib",
            "--with-lzma" if self.options.with_lzma else "--without-lzma",
            "--with-zstd" if self.options.get_safe("with_zstd") else "--without-zstd",
            "--enable-debuginfod" if self.options.debuginfod else "--disable-debuginfod",
        ])
        if Version(self.version) >= "0.186":
            tc.configure_args.append("--enable-libdebuginfod" if self.options.libdebuginfod else "--disable-libdebuginfod")
        tc.configure_args.append(f"BUILD_STATIC={'0' if self.options.shared else '1'}")
        if self.options.get_safe("with_zstd"):
            # ./configure ignores system_libs
            tc.extra_ldflags.append("-pthread")
        if self.options.shared and cross_building(self):
            # When cross-compiling shared libraries, the linker needs -rpath-link to resolve
            # transitive shared library dependencies (e.g. libdw.so -> libz.so) when linking
            # executables against elfutils' own shared libs.
            for dep in self.dependencies.host.values():
                for libdir in dep.cpp_info.aggregated_components().libdirs:
                    tc.extra_ldflags.append(f"-Wl,-rpath-link,{libdir}")
        tc.generate()
        if self.settings.compiler == "msvc":
            # Custom AutotoolsDeps for cl-like compilers
            # workaround for https://github.com/conan-io/conan/issues/12784
            cpp_info = CppInfo(self)
            for dependency in reversed(self.dependencies.host.topological_sort.values()):
                cpp_info.merge(dependency.cpp_info.aggregated_components())
            env = Environment()
            env.append("CPPFLAGS", [f"-I{unix_path(self, p)}" for p in cpp_info.includedirs] + [f"-D{d}" for d in cpp_info.defines])
            env.append("_LINK_", [lib if lib.endswith(".lib") else f"{lib}.lib" for lib in cpp_info.libs])
            env.append("LDFLAGS", [f"-L{unix_path(self, p)}" for p in cpp_info.libdirs] + cpp_info.sharedlinkflags + cpp_info.exelinkflags)
            env.append("CXXFLAGS", cpp_info.cxxflags)
            env.append("CFLAGS", cpp_info.cflags)
            env.vars(self).save_script("conanautotoolsdeps_cl_workaround")
        else:
            deps = AutotoolsDeps(self)
            deps.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def _patch_sources(self):
        if not self.options.i18n:
            replace_in_file(self, os.path.join(self.source_folder, "configure.ac"), "AM_GNU_GETTEXT", "# AM_GNU_GETTEXT")
            replace_in_file(self, os.path.join(self.source_folder, "Makefile.am"), " po ", " ")
        replace_in_file(self, os.path.join(self.source_folder, "config", "eu.am"),
                        "-Werror", "", strict=False)

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.autoreconf(args=["-fiv"])
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, pattern="COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # library components
        self.cpp_info.components["libelf"].set_property("pkg_config_name", "libelf")
        self.cpp_info.components["libelf"].libs = ["elf"]
        if self.options.i18n:
            self.cpp_info.components["libelf"].resdirs = ["share"]
        self.cpp_info.components["libelf"].requires = ["zlib-ng::zlib-ng"]
        if self.options.with_bzlib:
            self.cpp_info.components["libelf"].requires.append("bzip2::bzip2")
        if self.options.with_lzma:
            self.cpp_info.components["libelf"].requires.append("xz_utils::xz_utils")
        if self.options.get_safe("with_zstd"):
            self.cpp_info.components["libelf"].requires.append("zstd::zstd")
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["libelf"].system_libs.append("pthread")

        self.cpp_info.components["libdw"].set_property("pkg_config_name", "libdw")
        self.cpp_info.components["libdw"].libs = ["dw"]
        self.cpp_info.components["libdw"].requires = ["libelf"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libdw"].system_libs.extend(["dl"])

        self.cpp_info.components["libasm"].includedirs = ["include/elfutils"]
        self.cpp_info.components["libasm"].libs = ["asm"]
        self.cpp_info.components["libasm"].requires = ["libelf", "libdw"]

        if self.options.get_safe("libdebuginfod"):
            self.cpp_info.components["libdebuginfod"].set_property("pkg_config_name", "libdebuginfod")
            self.cpp_info.components["libdebuginfod"].libs = ["debuginfod"]
            self.cpp_info.components["libdebuginfod"].requires = ["libcurl::curl"]

        if self.context == "build":
            bin_ext = ".exe" if self.settings.os == "Windows" else ""
            for envvar, tool in [
                ("ADDR2LINE", "addr2line"),
                ("AR", "ar"),
                ("ELFCLASSIFY", "elfclassify"),
                ("ELFCMP", "elfcmp"),
                ("ELFCOMPRESS", "elfcompress"),
                ("ELFLINT", "elflint"),
                ("FINDTEXTREL", "findtextrel"),
                ("MAKE_DEBUG_ARCHIVE", "make-debug-archive"),
                ("NM", "nm"),
                ("OBJDUMP", "objdump"),
                ("RANLIB", "ranlib"),
                ("READELF", "readelf"),
                ("SIZE", "size"),
                ("STACK", "stack"),
                ("STRINGS", "strings"),
                ("STRIP", "strip"),
                ("UNSTRIP", "unstrip"),
            ]:
                self.buildenv_info.define_path(envvar, os.path.join(self.package_folder, "bin", f"eu-{tool}{bin_ext}"))
