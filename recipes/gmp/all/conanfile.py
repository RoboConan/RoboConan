import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.4"


class GmpConan(ConanFile):
    name = "gmp"
    description = (
        "GMP is a free library for arbitrary precision arithmetic, operating "
        "on signed integers, rational numbers, and floating-point numbers."
    )
    license = "LGPL-3.0-or-later OR GPL-2.0-or-later"
    homepage = "https://gmplib.org"
    topics = ("math", "arbitrary", "precision", "integer")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_assembly": [True, False],
        "enable_fat": [True, False],
        "enable_cxx": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_assembly": False,
        "enable_fat": False,
        "enable_cxx": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "yasm_wrapper.sh", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def config_options(self):
        # GMP does not export symbols for a shared build on Windows
        if self.settings.os == "Windows":
            del self.options.shared
            del self.options.fPIC
            self.package_type = "static-library"
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.enable_assembly
            del self.options.enable_fat

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        if self.options.get_safe("enable_fat"):
            self.options.enable_assembly.value = True
        if not self.options.enable_cxx:
            self.languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
            if is_msvc(self):
                self.tool_requires("yasm/[^1.3.0]")  # Needed for determining 32-bit word size
                self.tool_requires("automake/[^1.18.1]")  # Needed for lib-wrapper
        self.tool_requires("libtool/[*]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Disable unwanted subdirs
        replace_in_file(self, "Makefile.am",
                        "SUBDIRS = tests mpn mpz mpq mpf printf scanf rand cxx demos tune doc",
                        "SUBDIRS = mpn mpz mpq mpf printf rand cxx")
        # Don't embed compiler info
        replace_in_file(self, "gmp-h.in", '#define __GMP_CC "@CC@"', "")
        replace_in_file(self, "gmp-h.in", '#define __GMP_CFLAGS "@CFLAGS@"', "")

    def generate(self):
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        tc.configure_args.extend([
            f'--with-pic={yes_no(self.options.get_safe("fPIC", True))}',
            f'--enable-assembly={yes_no(not self.options.get_safe("enable_assembly"))}',
            f'--enable-fat={yes_no(self.options.get_safe("enable_fat"))}',
            f'--enable-cxx={yes_no(self.options.enable_cxx)}',
            '--srcdir=../src', # Use relative path to avoid issues with #include "$srcdir/gmp-h.in" on Windows
        ])
        if is_msvc(self):
            tc.configure_args.extend([
                "ac_cv_c_restrict=restrict",
                "ac_cv_func_memset=yes",
                "gmp_cv_asm_label_suffix=:",
                "gmp_cv_asm_w32=.word",
                "gmp_cv_check_libm_for_build=no",
                "lt_cv_deplibs_check_method=pass_all",
            ])
            tc.extra_cxxflags.append("-EHsc")
        env = tc.environment() # Environment must be captured *after* setting extra_cflags, etc. to pick up changes
        if is_msvc(self):
            yasm_wrapper = unix_path(self, os.path.join(self.source_folder, "yasm_wrapper.sh"))
            yasm_machine = {
                "x86": "x86",
                "x86_64": "amd64",
            }[str(self.settings.arch)]
            env.define("CCAS", f"{yasm_wrapper} -a x86 -m {yasm_machine} -p gas -r raw -f win32 -g null -X gnu")
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper"))
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f'{ar_wrapper} "lib -nologo"')
            env.define("NM", "dumpbin -nologo -symbols")
            tc.configure_args.append('nm_interface="MS dumpbin"')
        tc.generate(env)

    def _patch_sources(self):
        for it in self.conan_data.get("patches", {}).get(self.version, []):
            if "patch_os" not in it or self.settings.os == it["patch_os"]:
                entry = it.copy()
                patch_file = entry.pop("patch_file")
                patch_file_path = os.path.join(self.export_sources_folder, patch_file)
                if "patch_description" not in entry:
                    entry["patch_description"] = patch_file
                patch(self, patch_file=patch_file_path, **entry)

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.autoreconf()
        # fix build error on C++23 due to removal of unprototyped functions (#27479)
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "void g(){}",
                        "void g(int a,t1 const* b,t1 c,t2 d,t1 const* e,int f){}")
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYINGv2", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LESSERv3", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.components["libgmp"].set_property("pkg_config_name", "gmp")
        self.cpp_info.components["libgmp"].libs = ["gmp"]
        if self.settings.os != "Windows":
            self.cpp_info.components["libgmp"].system_libs = ["m"]

        if self.options.enable_cxx:
            self.cpp_info.components["gmpxx"].set_property("pkg_config_name", "gmpxx")
            self.cpp_info.components["gmpxx"].libs = ["gmpxx"]
            self.cpp_info.components["gmpxx"].requires = ["libgmp"]

        self.cpp_info.set_property("pkg_config_name", "_gmp_aggregate_")
