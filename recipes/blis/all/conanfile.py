import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfig, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.4"


class BlisConan(ConanFile):
    name = "blis"
    description = "BLIS is a software framework for instantiating high-performance BLAS-like dense linear algebra libraries"
    license = "BSD-3-Clause"
    homepage = "https://github.com/flame/blis"
    topics = ("hpc", "optimization", "matrix", "linear-algebra", "matrix-multiplication", "blas")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "interface": ["lp64", "ilp64"],
        "config": [
            # https://github.com/flame/blis/blob/master/docs/ConfigurationHowTo.md#walkthrough
            "auto", "generic",
            # Processor families
            # These will include support for all microarchitectures in the family
            "x86_64", "intel64", "amd64", "amd64_legacy", "arm64", "arm32",
            # intel64
            "skx", "knl", "haswell", "sandybridge", "penryn",
            # amd64
            "zen", "zen2", "zen3",
            # amd64_legacy
            "excavator", "steamroller", "piledriver", "bulldozer",
            # arm64
            "armsve", "firestorm", "thunderx2", "cortexa57", "cortexa53",
            # arm32
            "cortexa15", "cortexa9",
            # other
            "a64fx", "bgq", "power10", "power9",
        ],
        "threading": ["openmp", "pthread", "serial"],
        "complex_return": ["gnu", "intel"],
        "with_memkind": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "interface": "lp64",
        "config": "auto",
        "complex_return": "gnu",
        "threading": "openmp",
        "with_memkind": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]
    extension_properties = {"fortran_name_mangling": "lower_underscore"}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch == "x86_64":
            self.options.config = "intel64" if is_apple_os(self) else "x86_64"
        elif self.settings.arch == "armv8" and is_apple_os(self):
            self.options.config = "firestorm"
        elif self.settings.arch in ["armv8", "armv8.3", "arm64ec"]:
            self.options.config = "arm64"
        elif str(self.settings.arch).startswith("arm"):
            self.options.config = "arm32"
        else:
            self.options.config = "generic"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("BLIS does not support MSVC. Only GCC, Clang, and ICC are supported on Windows")

    def requirements(self):
        if self.options.threading == "openmp":
            self.requires("openmp/system")
        if self.options.with_memkind:
            self.requires("memkind/[*]", transitive_headers=True)

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _flags_from_pc(self, name):
        pc = PkgConfig(self, name, self.generators_folder)
        cflags = list(pc.cflags)
        cflags += [f"-I{unix_path(self, inc)}" for inc in pc.includedirs]
        ldflags = list(pc.linkflags)
        ldflags += [f"-L{unix_path(self, libdir)}" for libdir in pc.libdirs]
        ldflags += [f"-l{lib}" for lib in pc.libs]
        return cflags, ldflags

    def generate(self):
        tc = AutotoolsToolchain(self)
        # BLIS uses a custom configure script, remove unsupported standard autotools options
        allowed = {"--disable-shared", "--enable-shared", "--disable-static", "--enable-static", "--exec-prefix", "--includedir", "--libdir", "--sharedir", "--prefix"}
        tc.configure_args = [arg for arg in tc.configure_args if arg.split("=")[0] in allowed]
        tc.configure_args.append("--enable-cblas")
        tc.configure_args.append("--enable-rpath")
        if self.settings.build_type in ["Debug", "RelWithDebInfo"]:
            tc.configure_args.append("--enable-debug")
        int_size = 32 if self.options.interface == "lp64" else 64
        tc.configure_args.append(f"--blas-int-size={int_size}")
        threading = {"openmp": "openmp", "pthread": "pthreads", "serial": "single"}[str(self.options.threading)]
        tc.configure_args.append(f"--enable-threading={threading}")
        # tries to use $FC to determine --complex-return if not explicitly set
        tc.configure_args.append(f"--complex-return={self.options.complex_return}")
        tc.configure_args.append("--with-memkind" if self.options.with_memkind else "--without-memkind")
        tc.configure_args.append(str(self.options.config))
        if self.options.with_memkind:
            deps = PkgConfigDeps(self)
            deps.generate()
            cflags, ldflags = self._flags_from_pc("memkind")
            tc.extra_cflags += cflags
            tc.extra_ldflags += ldflags
            # The ./configure test only adds cflags
            tc.extra_ldflags += cflags
        # ./configure mangles paths with any @ symbols - override the generated config.mk values as a workaround
        tc_vars = tc.vars()
        tc.make_args.append(f"DIST_PATH={unix_path(self, self.source_folder)}")
        tc.make_args.append(f"CFLAGS_PRESET={tc_vars['CFLAGS']}")
        tc.make_args.append(f"LDFLAGS_PRESET={tc_vars['LDFLAGS']}")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "blis")
        self.cpp_info.libs = ["blis"]
        self.cpp_info.includedirs.append("include/blis")
        self.cpp_info.resdirs = ["share"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]
