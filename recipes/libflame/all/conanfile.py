import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, GnuToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.21"


class LibflameConan(ConanFile):
    name = "libflame"
    description = "Portable library for dense matrix computations (external BLAS/LAPACK only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/flame/libflame"
    topics = ("linear-algebra", "matrix-computations")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "blas3_frontend_control_trees": [True, False],
        "cuda": [True, False],
        "default_k_blocksize": [None, "ANY"],
        "default_m_blocksize": [None, "ANY"],
        "default_n_blocksize": [None, "ANY"],
        "internal_error_checking": ["full", "minimal", "none"],
        "ldim_alignment": [True, False],
        "memory_alignment": [None, "ANY"],
        "memory_leak_counter": [True, False],
        "non_critical_code": [True, False],
        "sse": [True, False],
        "supermatrix": [True, False],
        "threading": ["serial", "pthreads", "openmp"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "blas3_frontend_control_trees": False,
        "cuda": False,
        "default_k_blocksize": None,
        "default_m_blocksize": None,
        "default_n_blocksize": None,
        "internal_error_checking": "full",
        "ldim_alignment": False,
        "memory_alignment": None,
        "memory_leak_counter": False,
        "non_critical_code": True,
        "sse": False,
        "supermatrix": False,
        "threading": "serial",
    }
    options_description = {
        "blas3_frontend_control_trees": "Use libflame control trees for level-3 BLAS front ends",
        "cuda": "Build the CUDA SuperMatrix backend",
        "default_k_blocksize": "Override the default k-dimension block size",
        "default_m_blocksize": "Override the default m-dimension block size",
        "default_n_blocksize": "Override the default n-dimension block size",
        "internal_error_checking": "Select the default runtime parameter and object checking level",
        "ldim_alignment": "Pad leading dimensions so matrix columns begin at aligned addresses",
        "memory_alignment": "Align dynamic allocations to this power-of-two byte boundary",
        "memory_leak_counter": "Enable the runtime FLA_malloc/FLA_free balance counter",
        "non_critical_code": "Build non-critical functionality that may be omitted to reduce library size",
        "sse": "Enable the SSE vector intrinsics",
        "supermatrix": "Build the dependency-aware SuperMatrix task scheduler",
        "threading": "Select the internal multithreading model",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.sse

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        if self.options.cuda:
            self.options.supermatrix.value = True
        else:
            del self.settings.cuda
        if self.options.memory_alignment == None:
            self.options.rm_safe("ldim_alignment")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("blas/latest")
        self.requires("lapack/latest")
        if self.options.cuda:
            self.cuda.requires("cublas")
        if self.options.threading == "openmp":
            self.requires("openmp/system")

    def validate(self):
        if self.options.cuda:
            self.cuda.validate_settings()
        if self.dependencies["blas"].options.interface != "lp64":
            raise ConanInvalidConfiguration("libflame only supports the LP64 BLAS interface")
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        if mangling not in ["lower_underscore", "lower_no_underscore"]:
            raise ConanInvalidConfiguration(
                "libflame requires LAPACK with lower_underscore or lower_no_underscore name mangling"
            )

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "Makefile",
                        "install: libs install-libs install-lib-symlinks install-headers install-netlib-tests",
                        "install: libs install-libs install-lib-symlinks install-headers")

    def generate(self):
        AutotoolsDeps(self).generate()

        tc = GnuToolchain(self)
        if self.options.shared and self.settings.os != "Windows":
            tc.fpic = True
        for argument in ("--enable-shared", "--disable-shared", "--enable-static", "--disable-static"):
            tc.configure_args.pop(argument, None)
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        config_options = {
            "static-build": not self.options.shared,
            "dynamic-build": self.options.shared,
            "non-critical-code": self.options.non_critical_code,
            "builtin-blas": False,
            "external-lapack-interfaces": True,
            "external-lapack-for-subproblems": True,
            "supermatrix": self.options.supermatrix,
            "blas3-front-end-cntl-trees": self.options.blas3_frontend_control_trees,
            "ldim-alignment": self.options.get_safe("ldim_alignment", False),
            "memory-leak-counter": self.options.memory_leak_counter,
            "cblas-interfaces": True,
            "windows-build": self.settings.os == "Windows",
            "f77-no-underscore": mangling == "lower_no_underscore",
            "autodetect-f77-ldflags": False,
            "autodetect-f77-name-mangling": False,
            # Use the portable, bounded-command-line build paths and keep make output concise.
            "max-arg-list-hack": True,
            "portable-timer": self.settings.os != "Windows",
            "verbose-make-output": False,
            # Optimization and diagnostic flags are controlled by the Conan profile.
            "optimizations": False,
            "warnings": False,
            "debug": False,
            "profiling": False,
            "lto": False,
            # GotoBLAS internals are incompatible with a generic external BLAS provider.
            "goto-interfaces": False,
            "gpu": self.options.cuda,
            # HIP needs rocBLAS, rocSOLVER, HIP, and HSA runtime packages that RoboConan does not have yet.
            "hip": False,
            # Intel SCC and TI DSP require dedicated target toolchains that RoboConan does not support.
            "scc": False,
            "tidsp": False,
        }
        for option, enabled in config_options.items():
            tc.configure_args[f"--enable-{option}"] = "yes" if enabled else "no"

        threading = self.options.threading
        if threading == "serial":
            threading = "no"
        tc.configure_args["--enable-multithreading"] = threading
        tc.configure_args["--enable-vector-intrinsics"] = "sse" if self.options.get_safe("sse") else "none"
        if self.options.get_safe("memory_alignment") != None:
            tc.configure_args["--enable-memory-alignment"] = self.options.memory_alignment
        tc.configure_args["--enable-internal-error-checking"] = self.options.internal_error_checking
        tc.configure_args["--with-fc"] = "no"
        tc.configure_args["--with-python"] = "python3"
        for option in ("default_m_blocksize", "default_k_blocksize", "default_n_blocksize"):
            value = self.options.get_safe(option)
            if value != None:
                tc.configure_args[f"--enable-{option.replace('_', '-')}"] = value
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        Autotools(self).install()
        fix_apple_shared_install_name(self)

    def package_info(self):
        # The .pc names are unofficial and follow the naming from Homebrew/Spack
        self.cpp_info.set_property("pkg_config_name", "flame")
        self.cpp_info.set_property("pkg_config_aliases", ["libflame"])
        self.cpp_info.libs = ["libflame" if self.settings.os == "Windows" else "flame"]
        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.defines.append("FLA_DLL")
        if self.options.threading == "pthreads" and not self.options.shared:
            self.cpp_info.system_libs.append("pthread")
