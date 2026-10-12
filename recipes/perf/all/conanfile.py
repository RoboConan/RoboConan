import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import *
from conan.tools.gnu import Autotools, GnuToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class Perf(ConanFile):
    name = "perf"
    description = "Linux profiling with performance counters"
    license = "GPL-2.0 WITH Linux-syscall-note"
    homepage = "https://perf.wiki.kernel.org/index.php"
    topics = ("linux", "profiling")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler

    @property
    def _arch(self):
        return {
            "x86": "x86",
            "x86_64": "x86",
            "armv6": "arm",
            "armv7": "arm",
            "armv7hf": "arm",
            "armv8": "arm64",
            "armv8_32": "arm64",
            "armv8_64": "arm64",
            "ppc32": "powerpc",
            "ppc64": "powerpc",
            "ppc64le": "powerpc",
            "mips": "mips",
            "mips64": "mips",
            "sparc": "sparc",
            "sparcv9": "sparc",
            "s390": "s390",
            "s390x": "s390",
            "riscv32": "riscv",
            "riscv64": "riscv64"
        }.get(str(self.settings.arch))

    def requirements(self):
        self.requires("capstone/5.0.1")
        self.requires("libbpf/1.4.6")
        self.requires("libcap/[^2.69]")
        self.requires("elfutils/[>=0.191 <1]")
        self.requires("libnuma/[^2.0.16]")
        self.requires("libunwind/[^1.8.1]")
        self.requires("openssl/[<5]")
        self.requires("xz_utils/[^5.4.5]")
        self.requires("zstd/[~1.5]")
        # TODO: libtraceevent
        # TODO: babeltrace

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            raise ConanInvalidConfiguration("perf is supported only on Linux")

    def build_requirements(self):
        self.tool_requires("flex/[^2.6.4]")
        self.tool_requires("bison/[^3.8.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = GnuToolchain(self)
        tc_vars = tc.extra_env.vars(self)
        deps_vars = AutotoolsDeps(self).vars()
        tc.make_args["NO_LIBPYTHON"] = 1
        tc.make_args["NO_LIBPERL"] = 1
        tc.make_args["NO_LIBTRACEEVENT"] = 1
        tc.make_args["SRCARCH"] = self._arch
        tc.make_args["CC"] = tc_vars["CC"]
        tc.make_args["CPPFLAGS"] = deps_vars["CPPFLAGS"]
        tc.make_args["CPPFLAGS"] += f" -I{self.dependencies['openssl'].cpp_info.includedirs[0]}/openssl"
        tc.make_args["CFLAGS"] = deps_vars["CFLAGS"] + " " + tc.make_args["CPPFLAGS"]
        tc.make_args["LDFLAGS"] = deps_vars["LDFLAGS"]
        tc.make_args["LIBS"] = deps_vars["LIBS"]
        if not can_run(self):
            tc.make_args["HOSTCC"] = tc_vars.get("CC_FOR_BUILD", "cc")
            tc.make_args["LD"] = tc_vars["CC"]
            tc.make_args["STRIP"] = tc_vars["STRIP"]
            tc.make_args["OBJDUMP"] = tc.make_args["STRIP"].replace("strip", "objdump")
            tc.make_args["READELF"] = tc.make_args["STRIP"].replace("strip", "readelf")
        for val in list(tc.make_args):
            if not tc.make_args[val]:
                del tc.make_args[val]
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        with chdir(self, os.path.join(self.source_folder, "tools", "perf")):
            autotools.make()

    def package(self):
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSES/**",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "perf",
            src=os.path.join(self.source_folder, "tools", "perf"),
            dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
