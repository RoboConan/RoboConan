import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import stdcpp_library
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.4"


class BinutilsConan(ConanFile):
    name = "binutils"
    description = "The GNU Binutils are a collection of binary tools."
    package_type = "library"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/binutils"
    topics = ("gnu", "ld", "linker", "as", "assembler", "objcopy", "objdump")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "gprofng": [True, False],
        "i18n": [True, False],
        "multilib": [True, False],
        "target_triplet": [None, "ANY"],
        "prefix": [None, "ANY"],
        "add_unprefixed_to_path": [True, False],
        "with_zstd": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "gprofng": True,
        "i18n": False,
        "multilib": True,
        "target_triplet": None,
        "prefix": None,
        "add_unprefixed_to_path": True,
        "with_zstd": True,
    }

    python_requires = "conan-gnu-triplet/latest"
    python_requires_extend = "conan-gnu-triplet.TripletMixin"

    def layout(self):
        basic_layout(self, src_folder="src")

    def config_options(self):
        self.options.target_triplet = self.gnu_triplet_target or self.gnu_triplet_host
        self.options.prefix = f"{self.options.target_triplet}-"
        self.output.info(f"binutils:target_triplet={self.options.target_triplet}")

    def configure(self):
        if not self.options.gprofng:
            self.languages = ["C"]

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.options.add_unprefixed_to_path

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type="str"):
                self.tool_requires("msys2/latest")
        self.tool_requires("bison/[^3.8.2]")
        self.tool_requires("flex/[^2.6.4]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def requirements(self):
        # ctf-api.h
        self.requires("zlib-ng/[^2.0]", transitive_headers=True)
        if self.options.with_zstd:
            self.requires("zstd/[~1.5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _exec_prefix(self):
        return os.path.join("bin", "exec_prefix")

    def generate(self):
        def yes_no(opt): return "yes" if opt else "no"
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--enable-nls={yes_no(self.options.i18n)}")
        tc.configure_args.append(f"--target={self.options.target_triplet}")
        tc.configure_args.append(f"--enable-multilib={yes_no(self.options.multilib)}")
        tc.configure_args.append(f"--program-prefix={self.options.prefix}")
        tc.configure_args.append("--exec_prefix=/bin/exec_prefix")
        tc.configure_args.append(f"--enable-gprofng={yes_no(self.options.gprofng)}")
        tc.configure_args.append(f"--with-zlib={unix_path(self, self.dependencies['zlib-ng'].package_folder)}")
        tc.configure_args.append(f"--with-zstd={yes_no(self.options.with_zstd)}")
        # TODO
        tc.configure_args.append("--without-gmp")
        tc.configure_args.append("--without-isl")
        tc.configure_args.append("--without-mpc")
        tc.configure_args.append("--without-mpfr")
        tc.generate()
        if self.options.with_zstd:
            deps = PkgConfigDeps(self)
            deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        if not self.options.i18n:
            rmdir(self, os.path.join(self.package_folder, "share"))
        else:
            rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False,)

    def package_info(self):
        target_bindir = os.path.join(self._exec_prefix, str(self.options.target_triplet), "bin")
        self.cpp_info.bindirs = ["bin", target_bindir]
        if self.options.i18n:
            self.cpp_info.resdirs = ["share"]

        bindir = os.path.join(self.package_folder, "bin")
        absolute_target_bindir = os.path.join(self.package_folder, target_bindir)
        self.buildenv_info.append_path("PATH", bindir)
        if self.options.add_unprefixed_to_path:
            self.buildenv_info.append_path("PATH", absolute_target_bindir)

        self.conf_info.define("user.binutils:gnu_triplet", str(self.options.target_triplet))
        self.conf_info.define("user.binutils:prefix", str(self.options.prefix))

        self.cpp_info.resdirs = ["etc"]
        self.buildenv_info.define("GPROFNG_SYSCONFDIR", os.path.join(self.package_folder, "etc"))

        ## Libraries

        self.cpp_info.components["bfd"].libs = ["bfd"]
        self.cpp_info.components["bfd"].requires = ["sframe", "zlib-ng::zlib-ng"]
        if self.options.with_zstd:
            self.cpp_info.components["bfd"].requires.append("zstd::zstd")
        if self.settings.os in ["FreeBSD", "Linux"]:
            self.cpp_info.system_libs = ["dl", "rt"]

        self.cpp_info.components["ctf"].libs = ["ctf"]
        self.cpp_info.components["ctf"].requires = ["bfd"]

        self.cpp_info.components["ctf-nobfd"].libs = ["ctf-nobfd"]

        self.cpp_info.components["opcodes"].libs = ["opcodes"]
        self.cpp_info.components["opcodes"].requires = ["bfd"]

        self.cpp_info.components["sframe"].libs = ["sframe"]

        if self.options.gprofng:
            self.cpp_info.components["gprofng"].libs = ["gprofng"]
            self.cpp_info.components["gprofng"].requires = ["bfd", "opcodes"]
            if stdcpp_library(self):
                self.cpp_info.components["gprofng"].system_libs = [stdcpp_library(self)]
