import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, GnuToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, NMakeDeps

required_conan_version = ">=2.4"


class LibTomCryptConan(ConanFile):
    name = "libtomcrypt"
    description = ("LibTomCrypt is a cryptographic toolkit that provides well-known"
                   " published block ciphers, one-way hash functions, chaining modes,"
                   " pseudo-random number generators, public key cryptography and other routines.")
    license = "Unlicense"
    homepage = "https://www.libtom.net/"
    topics = ("cryptography", "encryption", "libtom")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "easy": [True, False],
        "argtype": [0, 1, 2, 3, 4],
        "no_test": [True, False],
        "no_file": [True, False],
        "small_code": [True, False],
        "small_stack": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "argtype": 0,
        "easy": False,
        "no_test": False,
        "no_file": False,
        "small_code": False,
        "small_stack": False,
    }
    options_description = {
        # see https://github.com/libtom/libtomcrypt/blob/v1.18.2/src/headers/tomcrypt_argchk.h
        "argtype": "Type of argument checking, 0=default, 1=fatal and 2=error+continue, 3=nothing, 4=return value",
        "easy": "Build just a subset of all the algos",
        "no_test": "Remove all algorithm self-tests from the library",
        "no_file": "Remove all API functions requiring a pre-defined FILE data-type (mostly useful for embedded targets)",
        "small_code": "Use small code where possible",
        "small_stack": "Always use small stack sizes where possible",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, f"tomcrypt-{self.version}.def", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libtommath/[^1.3.0]")

    def build_requirements(self):
        if not is_msvc(self):
            if self.options.shared:
                self.tool_requires("libtool/[^2.4.7]")
            if self.settings_build.os == "Windows":
                self.tool_requires("make/[^4.4.1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "makefile_include.mk",
                        "PKG_CONFIG_PATH=$(LIBPATH)/pkgconfig pkg-config",
                        self.conf.get("tools.gnu:pkg_config", default="pkgconf", check_type=str))

    @property
    def _defines(self):
        # https://github.com/libtom/libtomcrypt/blob/2e441a1/src/headers/tomcrypt_custom.h#L139-L177
        defines = ["LTM_DESC"]
        if self.options.easy:
            defines.append("LTC_EASY")
        if self.options.no_test:
            defines.append("LTC_NO_TEST")
        if self.options.no_file:
            defines.append("LTC_NO_FILE")
        if self.options.small_code:
            defines.append("LTC_SMALL_CODE")
        if self.options.small_stack:
            defines.append("LTC_SMALL_STACK")
        return defines

    def generate(self):
        if not cross_building(self):
            venv = VirtualRunEnv(self)
            venv.generate(scope="build")

        tc = GnuToolchain(self)
        if self.settings.os == "Windows" and not is_msvc(self):
            tc.ldflags.append("-lcrypt32")
        tc.extra_defines = self._defines
        tc.extra_defines.append("USE_LTM")
        tc.extra_defines.append(f"ARGTYPE={self.options.argtype}")
        cflags = tc.cflags + [f"-D{d}" for d in list(tc.defines) + list(tc.extra_defines)]
        ldflags = list(tc.ldflags)
        deps = AutotoolsDeps(self)
        dep_vars = deps.environment.vars(self)
        cflags.append(dep_vars.get("CFLAGS", ""))
        cflags.append(dep_vars.get("CPPFLAGS", ""))
        ldflags.append(dep_vars.get("LDFLAGS", ""))
        tc.make_args["CFLAGS"] = " ".join(cflags)
        tc.make_args["LDFLAGS"] = " ".join(ldflags)
        tc_vars = tc.extra_env.vars(self)
        if "CC" in tc_vars.keys():
            tc.make_args["CC"] = tc_vars["CC"]
        if cross_building(self):
            tc.make_args["CROSS_COMPILE"] = tc_vars["STRIP"].rsplit("strip", 1)[0]
        tc.extra_env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        tc.generate()

        if is_msvc(self):
            deps = NMakeDeps(self)
            deps.generate()
        else:
            deps = PkgConfigDeps(self)
            deps.generate()

    @property
    def _makefile(self):
        if self.settings.os == "Windows":
            return "makefile.mingw"
        else:
            if self.options.shared:
                return "makefile.shared"
            else:
                return "makefile.unix"

    def build(self):
        with chdir(self, self.source_folder):
            if is_msvc(self):
                if self.options.shared:
                    target = "tomcrypt.dll"
                else:
                    target = "tomcrypt.lib"
                self.run(f"nmake -f makefile.msvc {target}")
            else:
                if self.options.shared:
                    if self.settings.os == "Windows":
                        target = "libtomcrypt.dll"
                    else:
                        target = "libtomcrypt.la"
                else:
                    target = "libtomcrypt.a"
                autotools = Autotools(self)
                autotools.make(target=target, makefile=self._makefile)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "Windows":
            # The mingw makefile uses `cmd`, which is only available on Windows
            copy(self, "*.a", self.source_folder, os.path.join(self.package_folder, "lib"))
            copy(self, "*.lib", self.source_folder, os.path.join(self.package_folder, "lib"))
            copy(self, "*.dll", self.source_folder, os.path.join(self.package_folder, "bin"))
            copy(self, "tomcrypt*.h",
                 os.path.join(self.source_folder, "src", "headers"),
                 os.path.join(self.package_folder, "include"))
        else:
            with chdir(self, self.source_folder):
                autotools = Autotools(self)
                autotools.make(target="install", args=[f"PREFIX={self.package_folder}"], makefile=self._makefile)
            if not self.options.shared:
                rm(self, "*.a", os.path.join(self.package_folder, "lib"))

        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        if is_msvc(self) and self.options.shared:
            rename(self, os.path.join(self.package_folder, "lib", "tomcrypt.dll.lib"),
                   os.path.join(self.package_folder, "lib", "tomcrypt.lib"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libtomcrypt")
        self.cpp_info.libs = ["tomcrypt"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["advapi32", "crypt32"]
        self.cpp_info.defines = self._defines
