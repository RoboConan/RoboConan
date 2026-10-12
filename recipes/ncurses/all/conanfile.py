import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools import CppInfo
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import cross_building, stdcpp_library
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import Autotools, PkgConfigDeps, GnuToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime, unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class NCursesConan(ConanFile):
    name = "ncurses"
    description = "The ncurses (new curses) library is a free software emulation of curses in System V Release 4.0 (SVr4), and more"
    license = "X11"
    homepage = "https://www.gnu.org/software/ncurses"
    topics = ("terminal", "screen", "tui")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_widec": [True, False],
        "with_extended_colors": [True, False],
        "with_cxx": [True, False],
        "with_progs": [True, False],
        "with_ticlib": ["auto", True, False],
        "with_reentrant": [True, False],
        "with_tinfo": ["auto", True, False],
        "with_pcre2": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_widec": True,
        "with_extended_colors": True,
        "with_cxx": True,
        "with_progs": True,
        "with_ticlib": "auto",
        "with_reentrant": False,
        "with_tinfo": "auto",
        "with_pcre2": False,
    }

    @property
    def _is_mingw(self):
        return self.settings.os == "Windows" and self.settings.compiler == "gcc"

    def export_sources(self):
        copy(self, "*.cmake", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        # Set the default value based on OS
        self.options.with_ticlib = self.settings.os != "Windows"
        self.options.with_tinfo = self.settings.os != "Windows"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cxx:
            self.settings.rm_safe("compiler.libcxx")
            self.settings.rm_safe("compiler.cppstd")
        if not self.options.with_widec:
            self.options.rm_safe("with_extended_colors")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_pcre2:
            self.requires("pcre2/[^10.42]")
        if is_msvc(self):
            self.requires("getopt-for-visual-studio/20200201")
            self.requires("dirent/1.24")
            if self.options.get_safe("with_extended_colors"):
                self.requires("naive-tsearch/0.1.1")

    @property
    def _need_strip_from_toolchain(self):
        return cross_building(self) and not is_msvc(self) and not is_apple_os(self)

    def validate_build(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if self._need_strip_from_toolchain and not "strip" in executables:
            raise ConanInvalidConfiguration("Cross-building requires 'strip' tool to be defined in 'tools.build:compiler_executables'")

    def validate(self):
        if cross_building(self) and ("arm" in str(self.settings.arch) or "arm" in str(self.settings_build.arch)):
            # FIXME: Cannot build ncurses from x86_64 to armv8 (Apple M1).  Cross building from Linux/x86_64 to Mingw/x86_64 works flawless.
            # FIXME: Need access to environment of build profile to set build compiler (BUILD_CC/CC_FOR_BUILD)
            raise ConanInvalidConfiguration("Cross building to/from arm is (currently) not supported")
        if self.options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration("Cannot build shared libraries with static (MT) runtime")
        if self.settings.os == "Windows":
            if self.options.with_tinfo:
                raise ConanInvalidConfiguration("terminfo cannot be built on Windows because it requires a term driver")
            if self.options.shared and self.options.with_ticlib:
                raise ConanInvalidConfiguration("ticlib cannot be built separately as a shared library on Windows")

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = GnuToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        tc.configure_args["--with-shared"] = yes_no(self.options.shared)
        tc.configure_args["--with-cxx-shared"] = yes_no(self.options.shared)
        tc.configure_args["--with-normal"] = yes_no(not self.options.shared)
        tc.configure_args["--enable-widec"] = yes_no(self.options.with_widec)
        tc.configure_args["--enable-ext-colors"] = yes_no(self.options.get_safe("with_extended_colors"))
        tc.configure_args["--enable-reentrant"] = yes_no(self.options.with_reentrant)
        tc.configure_args["--with-pcre2"] = yes_no(self.options.with_pcre2)
        tc.configure_args["--with-cxx-binding"] = yes_no(self.options.with_cxx)
        tc.configure_args["--with-progs"] = yes_no(self.options.with_progs)
        tc.configure_args["--with-termlib"] = yes_no(self.options.with_tinfo)
        tc.configure_args["--with-ticlib"] = yes_no(self.options.with_ticlib)
        tc.configure_args["--with-libtool"] = "no"
        tc.configure_args["--with-ada"] = "no"
        tc.configure_args["--with-manpages"] = "no"
        tc.configure_args["--with-tests"] = "no"
        tc.configure_args["--enable-echo"] = "no"
        tc.configure_args["--with-debug"] = "no"
        tc.configure_args["--with-profile"] = "no"
        tc.configure_args["--with-sp-funcs"] = "yes"
        tc.configure_args["--enable-rpath"] = "no"
        tc.configure_args["--enable-pc-files"] = "no"
        if cross_building(self):
            tc_vars = tc.extra_env.vars(self)
            tc.configure_args["--with-build-cc"] = tc_vars.get("CC_FOR_BUILD", "cc")
        build = None
        host = None
        if self.settings.os == "Windows":
            tc.configure_args["--enable-macros"] = "no"
            tc.configure_args["--enable-termcap"] = "no"
            tc.configure_args["--enable-database"] = "yes"
            tc.configure_args["--enable-sp-funcs"] = "yes"
            tc.configure_args["--enable-term-driver"] = "yes"
            tc.configure_args["--enable-interop"] = "yes"
        if is_msvc(self):
            build = host = f"{self.settings.arch}-w64-mingw32-msvc"
            tc.configure_args["ac_cv_func_getopt"] = "yes"
            tc.configure_args["ac_cv_func_setvbuf_reversed"] = "no"
            # The env vars below are used by ./configure, but not during make
            tc.make_args["CC"] = "cl -nologo"
            tc.make_args["CPP"] = "cl -nologo -E"
            tc.extra_cxxflags.append("-EHsc")
            if self.options.get_safe("with_extended_colors"):
                tc.extra_cflags.append(" ".join(f"-I{dir}" for dir in self.dependencies["naive-tsearch"].cpp_info.includedirs))
                tc.extra_ldflags.append(" ".join(f"-l{lib}" for lib in self.dependencies["naive-tsearch"].cpp_info.libs))
        if self._is_mingw:
            # add libssp (gcc support library) for some missing symbols (e.g. __strcpy_chk)
            tc.extra_ldflags.extend(["-lmingwex", "-lssp"])
        if build:
            tc.configure_args["ac_cv_build"] = build
        if host:
            tc.configure_args["ac_cv_host"] = host
            tc.configure_args["ac_cv_target"] = host
        # Allow ncurses to set the include dir with an appropriate subdir
        tc.configure_args.pop("--includedir", None)
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) >= 15:
            # FIXME: Workaround to allow building with with GCC15
            # Upstream has proper but huge patches: https://invisible-island.net/ncurses/NEWS.html#index-t20241207
            tc.extra_cflags.append("-std=gnu17")
        tc.generate()

        if is_msvc(self):
            # Custom AutotoolsDeps for cl like compilers
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

        deps = PkgConfigDeps(self)
        deps.generate()

    def _patch_sources(self):
        if self._need_strip_from_toolchain:
            # https://forums.raspberrypi.com/viewtopic.php?p=1559247&sid=8c8904db75c823abdeeecfc761a76e3f#p1559247
            replace_in_file(self, os.path.join(self.source_folder, "configure"),
                            'INSTALL_OPT_S="-s"',
                            'INSTALL_OPT_S="-s --strip-program=${STRIP}"')

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        os.unlink(os.path.join(self.package_folder, "bin", f"ncurses{self._suffix}{Version(self.version).major}-config"))
        copy(self, "*.cmake",
             src=os.path.join(self.export_sources_folder, "cmake"),
             dst=os.path.join(self.package_folder, self._module_subfolder))
        fix_apple_shared_install_name(self)

    @property
    def _suffix(self):
        res = ""
        # https://github.com/mirror/ncurses/blob/v6.4/configure.in#L1393
        if self.options.with_reentrant:
            res += "t"
        # https://github.com/mirror/ncurses/blob/v6.4/configure.in#L959
        if self.options.with_widec:
            res += "w"
        return res

    @property
    def _lib_suffix(self):
        res = self._suffix
        if self.options.shared:
            if self.settings.os == "Windows":
                res += ".dll"
        return res

    @property
    def _module_subfolder(self):
        return os.path.join("lib", "cmake")

    @property
    def _module_file(self):
        return f"conan-official-{self.name}-targets.cmake"

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "Curses")

        # CMake's standard FindCurses module does not define a target.
        # Adding one nevertheless for consistency with other packages.
        # https://gitlab.kitware.com/cmake/cmake/-/issues/23051
        self.cpp_info.set_property("cmake_target_name", "Curses::Curses")

        def _add_component(name, lib_name=None, requires=None):
            lib_name = lib_name or name
            self.cpp_info.components[name].libs = [lib_name + self._lib_suffix]
            self.cpp_info.components[name].set_property("pkg_config_name", lib_name + self._lib_suffix)
            self.cpp_info.components[name].includedirs.append(os.path.join("include", "ncurses" + self._suffix))
            self.cpp_info.components[name].requires = requires if requires else []

        _add_component("libcurses", lib_name="ncurses")
        _add_component("panel", requires=["libcurses"])
        _add_component("menu", requires=["libcurses"])
        _add_component("form", requires=["libcurses"])

        if self.options.with_tinfo:
            _add_component("tinfo")
            self.cpp_info.components["libcurses"].requires += ["tinfo"]

        if self.options.with_ticlib:
            _add_component("ticlib", lib_name="tic", requires=["libcurses"])

        if self.options.with_cxx:
            _add_component("curses++", lib_name="ncurses++", requires=["libcurses"])
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["libcurses++"].system_libs.append("util")
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.components["libcurses++"].system_libs.append(libcxx)

        if is_msvc(self):
            self.cpp_info.components["libcurses"].requires += [
                "getopt-for-visual-studio::getopt-for-visual-studio",
                "dirent::dirent",
            ]
            if self.options.get_safe("with_extended_colors"):
                self.cpp_info.components["libcurses"].requires += [
                    "naive-tsearch::naive-tsearch"
                ]
        if self.options.with_pcre2:
            self.cpp_info.components["form"].requires.append("pcre2::pcre2")

        if not self.options.shared:
            self.cpp_info.components["libcurses"].defines = ["NCURSES_STATIC"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["libcurses"].system_libs = ["dl", "m"]

        module_rel_path = os.path.join(self._module_subfolder, self._module_file)
        self.cpp_info.components["libcurses"].builddirs.append(self._module_subfolder)
        self.cpp_info.set_property("cmake_build_modules", [module_rel_path])

        terminfo = os.path.join(self.package_folder, "share", "terminfo")
        self.buildenv_info.define_path("TERMINFO", terminfo)
        self.runenv_info.define_path("TERMINFO", terminfo)
        self.conf_info.define("user.ncurses:lib_suffix", self._lib_suffix)
