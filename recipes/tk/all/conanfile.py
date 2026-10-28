import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import NMakeDeps, NMakeToolchain, is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class TkConan(ConanFile):
    name = "tk"
    description = "Tk is a graphical user interface toolkit that takes developing desktop applications to a higher level than conventional approaches."
    topics = ("conan", "tk", "gui", "tcl", "scripting", "programming")
    homepage = "https://tcl.tk"
    license = "TCL"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_atk": [True, False],
        "with_bidi": [True, False],
        "with_libcups": [True, False],
        "with_xft": [True, False],
        "with_xrender": [True, False],
        "with_xss": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_atk": False,
        "with_bidi": True,
        "with_libcups": False,
        "with_xft": True,
        "with_xrender": True,
        "with_xss": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_atk
            del self.options.with_bidi
            del self.options.with_libcups
            del self.options.with_xft
            del self.options.with_xrender
            del self.options.with_xss

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.get_safe("with_bidi"):
            self.options.with_xft = True

    def requirements(self):
        self.requires(f"tcl/{self.version}", transitive_headers=True, transitive_libs=True)
        if self.settings.os in ["Linux", "FreeBSD"]:
            # Used in public tk.h
            self.requires("xorg/system", transitive_headers=True)
            if self.options.with_xft:
                self.requires("fontconfig/[^2.13]")
                self.requires("libxft/[^2.3]")
            if self.options.with_bidi:
                self.requires("harfbuzz/[>=2.8]")
                self.requires("sheenbidi/[^3.0]")
            if self.options.with_libcups:
                self.requires("libcups/[^2.2]")
            if self.options.with_atk:
                self.requires("at-spi2-core/[^2.53]")

    def build_requirements(self):
        self.tool_requires("automake/[^1.18.1]")
        if self.settings.os in ["Linux", "FreeBSD"]:
            if not self.conf.get("tools.gnu:pkg_config", check_type=str):
                self.tool_requires("pkgconf/[<4]")
        if not is_msvc(self):
            if (
                self.settings_build.os == "Windows"
                and not self.conf.get("tools.microsoft.bash:path")
                and not self.conf.get("tools.microsoft.bash:subsystem")
            ):
                self.tool_requires("msys2/latest")

    def validate(self):
        if self.dependencies["tcl"].options.shared != self.options.shared:
            raise ConanInvalidConfiguration("The shared option of tcl and tk must have the same value")
        if (self.options.get_safe("with_atk")
                and not self.dependencies["at-spi2-core"].options.shared):
            raise ConanInvalidConfiguration("Tk accessibility support requires shared at-spi2-core")
        if self.settings.os == "Macos" and cross_building(self):
            raise ConanInvalidConfiguration("The tk conan recipe does not currently support Macos cross-builds. A contribution to add this functionality would be welcome.")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        makefile = os.path.join(self.source_folder, "unix", "Makefile.in")
        replace_in_file(self, makefile, "LDFLAGS			= @LDFLAGS_DEFAULT@ @LDFLAGS@", "")
        replace_in_file(self, makefile, " ${CFLAGS}", " ${CFLAGS} ${CPPFLAGS}")
        # Tk 9.1 vendors SheenBidi 3.0.0 as a unity source. Use the standalone
        # dependency instead, while retaining upstream's HarfBuzz integration.
        for configure_name in ["configure", "configure.ac"]:
            configure = os.path.join(self.source_folder, "unix", configure_name)
            replace_in_file(self, configure,
                            'UNIX_FONT_OBJS="tkUnixBidiFont.o SheenBidi.o"',
                            'UNIX_FONT_OBJS="tkUnixBidiFont.o"')
            replace_in_file(self, configure,
                            'BIDI_CFLAGS="-I${TK_SRC_DIR}/unix/bidi/Headers \\\n\t\t     -I${TK_SRC_DIR}/unix/bidi/Source \\\n\t\t     -I${TK_SRC_DIR}/unix/bidi \\\n\t\t     -DSB_CONFIG_UNITY -DSB_CONFIG_EXPERIMENTAL_TEXT_API -w"',
                            'BIDI_CFLAGS="`pkg-config --cflags sheenbidi`"')
            replace_in_file(self, configure,
                            'HB_LIBS=`pkg-config --libs harfbuzz`',
                            'HB_LIBS="`pkg-config --libs harfbuzz` `pkg-config --libs sheenbidi`"')
            replace_in_file(self, configure,
                            "found_cups=`cups-config 2>/dev/null`",
                            "found_cups=`pkg-config --exists cups 2>/dev/null && echo yes`")
            replace_in_file(self, configure,
                            'CUPS_CFLAGS="-DHAVE_CUPS"',
                            'CUPS_CFLAGS="-DHAVE_CUPS `pkg-config --cflags cups`"')
            replace_in_file(self, configure,
                            "CUPS_LIBS=`cups-config --libs`",
                            "CUPS_LIBS=`pkg-config --libs cups`")
        rmdir(self, os.path.join(self.source_folder, "unix", "bidi"))

        # NMake's inline file syntax otherwise creates a malformed output path.
        replace_in_file(self, os.path.join(self.source_folder, "win", "makefile.vc"),
                        "@type << > $(OUT_DIR)\\pkgIndex.tcl",
                        "@type <<$(OUT_DIR)\\pkgIndex.tcl")

    def generate(self):
        if is_msvc(self):
            tc = NMakeToolchain(self)
            tc.generate()

            deps = NMakeDeps(self)
            deps.generate()
        else:
            # Inject runenv variables into buildenv
            # This is required because tcl needs to be available when configure tries to
            # run a test executable
            if not cross_building(self):
                runenv = VirtualRunEnv(self)
                runenv.generate(scope="build")

            yes_no = lambda v: "yes" if v else "no"
            tc = AutotoolsToolchain(self)
            # Tk's configure script does not use the standard Autotools static
            # switches. Static/shared selection is inferred from --enable-shared.
            tc.update_configure_args({
                "--enable-static": None,
                "--disable-static": None,
            })
            tcl_root = self.dependencies['tcl'].package_folder
            tc.configure_args.extend([
                # Keep the script library available to arbitrary consumers of
                # the static library instead of embedding it as an archive tail.
                "--disable-zipfs",
                f"--enable-symbols={yes_no(self.settings.build_type == 'Debug')}",
                f"--enable-64bit={yes_no(self.settings.arch == 'x86_64')}",
                f"--enable-aqua={yes_no(is_apple_os(self))}",
                f"--with-tcl={os.path.join(tcl_root, 'lib')}",
                f"--with-x={yes_no(self.settings.os in ['Linux', 'FreeBSD'])}",
            ])
            if self.settings.os in ["Linux", "FreeBSD"]:
                tc.configure_args.extend([
                    f"--enable-bidi={yes_no(self.options.with_bidi)}",
                    f"--enable-libcups={yes_no(self.options.with_libcups)}",
                    f"--enable-xft={yes_no(self.options.with_xft)}",
                    f"--enable-xrender={yes_no(self.options.with_xrender)}",
                    f"--enable-xss={yes_no(self.options.with_xss)}",
                ])
            tc.make_args.append(f"TCL_GENERIC_DIR={os.path.join(tcl_root, 'include')}")
            if self.settings.os in ["Linux", "FreeBSD"]:
                # Ensure the library has a soname, fix https://github.com/conan-io/conan-center-index/issues/27691
                # (mirror debian behavior)
                tc.configure_args.append("TK_SHLIB_LD_EXTRAS=-Wl,-soname,${TK_LIB_FILE}")
            if self.settings.os == "Windows":
                tc.extra_defines.extend(["UNICODE", "_UNICODE", "_ATL_XP_TARGETING"])
            if not is_apple_os(self):
                tc.extra_ldflags.append("-Wl,--as-needed")
            tc.generate()

            if self.settings.os in ["Linux", "FreeBSD"]:
                deps = PkgConfigDeps(self)
                deps.generate()

                # Only declared Conan dependencies participate in upstream's
                # ATK auto-detection.
                env = Environment()
                env.define_path("PKG_CONFIG_LIBDIR", self.generators_folder)
                env.vars(self).save_script("conan_pkg_config")

    def _get_default_build_system(self):
        if is_apple_os(self):
            return "unix"
        elif self.settings.os in ("Linux", "FreeBSD"):
            return "unix"
        elif self.settings.os == "Windows":
            return "win"
        else:
            raise ValueError("tk recipe does not recognize os")

    def _get_configure_folder(self, build_system=None):
        if build_system is None:
            build_system = self._get_default_build_system()
        if build_system not in ["win", "unix", "macosx"]:
            raise ConanException(f"Invalid build system: {build_system}")
        return os.path.join(self.source_folder, build_system)

    def _build_nmake(self, target="release"):
        # https://core.tcl.tk/tips/doc/trunk/tip/477.md
        opts = ["noembed"]
        if not self.options.shared:
            opts.append("static")
        if self.settings.build_type == "Debug":
            opts.append("symbols")
        if "dynamic" in str(self.settings.compiler.runtime) or "MD" in str(self.settings.compiler.runtime):
            opts.append("msvcrt")
        else:
            opts.append("nomsvcrt")
        if "d" not in str(self.settings.compiler.runtime):
            opts.append("unchecked")
        # https://core.tcl.tk/tk/tktview?name=3d34589aa0
        # https://wiki.tcl-lang.org/page/Building+with+Visual+Studio+2017
        tcl_lib_path = os.path.join(self.dependencies["tcl"].package_folder, "lib")
        tclimplib, tclstublib = None, None
        for lib in os.listdir(tcl_lib_path):
            suffix = "".join(self.version.split(".")[:2])
            if not lib.endswith(".lib"):
                continue
            if lib.startswith(f"tcl{suffix}"):
                tclimplib = os.path.join(tcl_lib_path, lib)
            elif lib == "tclstub.lib":
                tclstublib = os.path.join(tcl_lib_path, lib)

        if tclimplib is None or tclstublib is None:
            raise ConanException("tcl dependency misses tcl and/or tclstub library")

        flags = {
            "INSTALLDIR": self.package_folder,
            "OPTS": ",".join(opts),
            "TCLDIR": self.dependencies["tcl"].package_folder,
            "TCL_LIBRARY": self.dependencies["tcl"].runenv_info.vars(self).get("TCL_LIBRARY"),
            "TCLIMPLIB": tclimplib,
            "TCLSTUBLIB": tclstublib,
        }
        config_dir = self._get_configure_folder("win")
        with chdir(self, config_dir):
            args = " ".join(f'{k}="{v}"' for k, v in flags.items())
            self.run(f"nmake -nologo -f makefile.vc {args} {target}")

    def build(self):
        if is_msvc(self):
            self._build_nmake()
        else:
            autotools = Autotools(self)
            autotools.configure(build_script_folder=self._get_configure_folder())
            autotools.make()

    def package(self):
        copy(self, "license.terms", self.source_folder, os.path.join(self.package_folder, "licenses"),)
        if is_msvc(self):
            self._build_nmake("install")
        else:
            with chdir(self, self.build_folder):
                autotools = Autotools(self)
                autotools.install()
                # DESTDIR is only default initialized for target="install"
                autotools.make(
                    target="install-private-headers",
                    args=[f"DESTDIR={self.package_folder}"],
                )
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "man"))
        rmdir(self, os.path.join(self.package_folder, "share"))

        tkConfigShPath = os.path.join(self.package_folder, "lib", "tkConfig.sh")
        if os.path.exists(tkConfigShPath):
            for variable in ["TK_BUILD_LIB_SPEC", "TK_SRC_DIR", "TK_BUILD_STUB_LIB_SPEC", "TK_BUILD_STUB_LIB_PATH"]:
                replace_in_file(self, tkConfigShPath, f"\n{variable}=", f"\n#{variable}=")
            # This can only be modified after build since the value being replaced is a result
            # of variable substitution in tkConfig.sh.in
            replace_in_file(self, tkConfigShPath, "//", "${TK_ROOT}/")
            tk_config = load(self, tkConfigShPath)
            for dependency in self.dependencies.host.values():
                if dependency.package_folder and dependency.package_folder in tk_config:
                    if not os.path.isdir(os.path.join(dependency.package_folder, "lib")):
                        libdir = f"-L{dependency.package_folder}/lib "
                        if libdir in tk_config:
                            replace_in_file(self, tkConfigShPath, libdir, "")
                            tk_config = tk_config.replace(libdir, "")
                        continue
                    name = str(dependency.ref.name).upper().replace("-", "_")
                    replacement = f"${{CONAN_TK_{name}_ROOT}}"
                    replace_in_file(self, tkConfigShPath, dependency.package_folder, replacement)
                    tk_config = tk_config.replace(dependency.package_folder, replacement)

        fix_apple_shared_install_name(self)

    def package_info(self):
        v = Version(self.version)
        lib_infix = f"{v.major}.{v.minor}"
        if is_msvc(self):
            lib_infix = f"{v.major}{v.minor}"
            tk_suffix = "" if self.options.shared else "s"
            if not self.options.shared and is_msvc_static_runtime(self):
                tk_suffix += "x"
        else:
            tk_suffix = ""
        self.cpp_info.libs = [f"tcl{v.major}tk{lib_infix}{tk_suffix}", "tkstub"]
        self.cpp_info.requires = ["tcl::tcl"]
        if self.settings.os == "Macos":
            self.cpp_info.frameworks = ["CoreFoundation", "Cocoa", "Carbon", "IOKit", "QuartzCore", "UniformTypeIdentifiers"]
            self.cpp_info.exelinkflags = ["-ObjC"]
            self.cpp_info.sharedlinkflags = ["-ObjC"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = [
                "netapi32",
                "kernel32",
                "user32",
                "advapi32",
                "userenv",
                "ws2_32",
                "gdi32",
                "comdlg32",
                "imm32",
                "comctl32",
                "shell32",
                "uuid",
                "ole32",
                "oleaut32",
                "oleacc",
                "usp10",
                "dwmapi",
                "msimg32",
            ]
        elif self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.requires.append("xorg::x11")
            if self.options.with_xft:
                self.cpp_info.requires.extend(["fontconfig::fontconfig", "libxft::libxft"])
            if self.options.with_bidi:
                self.cpp_info.requires.extend(["harfbuzz::harfbuzz_", "sheenbidi::sheenbidi"])
            if self.options.with_xrender:
                self.cpp_info.requires.append("xorg::xrender")
            if self.options.with_xss:
                self.cpp_info.requires.extend(["xorg::xext", "xorg::xscrnsaver"])
            if self.options.with_libcups:
                self.cpp_info.requires.append("libcups::libcups")
            if self.options.with_atk:
                self.cpp_info.requires.extend(["at-spi2-core::atk", "at-spi2-core::atk-bridge"])

        tk_library = os.path.join(self.package_folder, "lib", f"{self.name}{v.major}.{v.minor}",).replace("\\", "/")
        self.runenv_info.define("TK_LIBRARY", tk_library)

        tk_root = self.package_folder.replace("\\", "/")
        self.runenv_info.define("TK_ROOT", tk_root)

        tk_config = os.path.join(self.package_folder, "lib", "tkConfig.sh")
        tk_config = load(self, tk_config) if os.path.exists(tk_config) else ""
        for dependency in self.dependencies.host.values():
            if dependency.package_folder:
                name = str(dependency.ref.name).upper().replace("-", "_")
                var = f"CONAN_TK_{name}_ROOT"
                if f"${{{var}}}" in tk_config:
                    self.buildenv_info.define_path(var, dependency.package_folder)
