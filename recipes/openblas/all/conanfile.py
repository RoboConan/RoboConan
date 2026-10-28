import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime, is_msvc

required_conan_version = ">=2.1"

# Maps Conan's settings.arch to the corresponding OpenBLAS TARGET:
conan_arch_to_openblas_target = {
    "x86": "SANDYBRIDGE",  # Sandy bridge was discontinued in September of 2013,
    "x86_64": "SANDYBRIDGE",  # supporting older CPUs is a performance trade-off
    "ppc32be": None,  # TODO: OpenBLAS has POWER4, POWER5, POWER6, POWER7,
    "ppc32": None,  #         POWER8, POWER9, POWER10, POWER11, PPCG4, PPC970, PPC970MP,
    "ppc64le": None,  #       PPC440, PPC440FP2, CELL
    "ppc64": None,
    "armv4": None,  # Not supported by OpenBLAS
    "armv4i": None,  # Not supported by OpenBLAS
    "armv5el": "ARMV5",
    "armv5hf": "ARMV5",
    "armv6": "ARMV6",
    "armv7": "ARMV7",
    "armv7hf": "ARMV7",
    "armv7s": "ARMV7",
    "armv7k": "ARMV7",
    "armv8": "ARMV8",
    "armv8_32": "ARMV7",  # No 32-bit ARMv8 TARGET in OpenBLAS
    "armv8.3": "ARMV8",
    "arm64ec": "ARMV8",
    "sparc": None,  # TODO: OpenBLAS has SPARC, SPARCV7
    "sparcv9": None,
    "mips": None,  # TODO: OpenBLAS has P5600, MIPS1004K and MIPS24K
    "mips64": "MIPS64_GENERIC",
    "avr": None,  # Not supported by OpenBLAS
    "s390": None,  # Not supported by OpenBLAS
    "s390x": "ZARCH_GENERIC",
    "asm.js": "WASM128_GENERIC",
    "wasm": "WASM128_GENERIC",
    "sh4le": None,  # Not supported by OpenBLAS
    "e2k-v2": "E2K",
    "e2k-v3": "E2K",
    "e2k-v4": "E2K",
    "e2k-v5": "E2K",
    "e2k-v6": "E2K",
    "e2k-v7": "E2K",
    "riscv64": "RISCV64_GENERIC",
    "riscv32": None,  # Not supported by OpenBLAS
    "xtensalx6": None,  # Not supported by OpenBLAS
    "xtensalx106": None,  # Not supported by OpenBLAS
    "xtensalx7": None,  # Not supported by OpenBLAS
    "loongarch64": "LA64_GENERIC",
}

# Taken from OpenBLAS TargetList.txt
available_openblas_targets = ["P2", "KATMAI", "COPPERMINE", "NORTHWOOD", "PRESCOTT", "BANIAS", "YONAH", "CORE2", "PENRYN", "DUNNINGTON", "NEHALEM", "SANDYBRIDGE", "HASWELL", "SKYLAKEX", "ATOM", "COOPERLAKE", "SAPPHIRERAPIDS", "ATHLON", "OPTERON", "OPTERON_SSE3", "BARCELONA", "SHANGHAI", "ISTANBUL", "BOBCAT", "BULLDOZER", "PILEDRIVER", "STEAMROLLER", "EXCAVATOR", "ZEN", "SSE_GENERIC", "VIAC3", "NANO", "POWER4", "POWER5", "POWER6", "POWER7", "POWER8", "POWER9", "POWER10", "POWER11", "PPCG4", "PPC970", "PPC970MP", "PPC440", "PPC440FP2", "CELL", "P5600", "MIPS1004K", "MIPS24K", "MIPS64_GENERIC", "SICORTEX", "LOONGSON3A", "LOONGSON3B", "I6400", "P6600", "I6500", "ITANIUM2", "SPARC", "SPARCV7", "CORTEXA15", "CORTEXA9", "ARMV7", "ARMV6", "ARMV5", "ARMV8", "CORTEXA53", "CORTEXA57", "CORTEXA72", "CORTEXA73", "CORTEXA76", "CORTEXA510", "CORTEXA710", "CORTEXX1", "CORTEXX2", "NEOVERSEN1", "NEOVERSEV1", "NEOVERSEN2", "NEOVERSEV2", "CORTEXA55", "EMAG8180", "FALKOR", "THUNDERX", "THUNDERX2T99", "TSV110", "THUNDERX3T110", "VORTEX", "VORTEXM4", "A64FX", "ARMV8SVE", "ARMV9SME", "FT2000", "ZARCH_GENERIC", "Z13", "Z14", "RISCV64_GENERIC", "RISCV64_ZVL128B", "C910V", "x280", "RISCV64_ZVL256B", "U74", "LOONGSONGENERIC", "LOONGSON3R5", "LOONGSON2K1000", "LA64_GENERIC", "LA264", "LA464", "E2K", "EV4", "EV5", "EV6", "CSKY", "CK860FV", "WASM128_GENERIC"]


class OpenblasConan(ConanFile):
    name = "openblas"
    description = "An optimized BLAS library based on GotoBLAS2, with LAPACK"
    license = "BSD-3-Clause"
    homepage = "https://www.openblas.net"
    topics = ("blas", "lapack")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "interface": ["lp64", "ilp64"],
        "threading": ["openmp", "pthread", "serial"],
        "build_lapack": [True, False],
        "build_relapack": [True, False],
        "build_bfloat16": [True, False],
        "use_locking": [True, False],
        "dynamic_arch": [True, False],
        "target": [None, "GENERIC"] + available_openblas_targets,
        "max_threads": ["auto", "ANY"],
        "max_omp_parallel": ["ANY"],
        "use_fortran": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "interface": "lp64",
        "threading": "openmp",
        "build_lapack": True,
        "build_relapack": True,
        "build_bfloat16": False,
        "use_locking": False,
        "dynamic_arch": False,
        "target": None,
        "max_threads": 128,
        "max_omp_parallel": 1,
        "use_fortran": True,
    }
    options_description = {
        "interface": "Optionally build with ILP64 interface instead of LP64 (incompatible with the standard API)",
        "threading": "Threading model to use: openmp, pthread or serial (no threading)",
        "build_lapack": "Build LAPACK and LAPACKE",
        "build_relapack": "Build with ReLAPACK (recursive implementation of several LAPACK functions on top of standard LAPACK)",
        "build_bfloat16": "Build with bfloat16 support",
        "use_locking": "Use locks even in single-threaded builds to make them callable from multiple threads",
        "dynamic_arch": "Include support for multiple CPU targets, with automatic selection at runtime (x86/x86_64, AArch64, Power, or RISC-V RVV 1.0 only)",
        "target": "OpenBLAS TARGET variable (see TargetList.txt)",
        "max_threads": "The maximum number of parallel threads you expect to need (defaults to the number of cores in the build cpu)",
        "max_omp_parallel": "Number of OpenMP instances that your code may use for parallel calls into OpenBLAS",
        "use_fortran": "Build LAPACK from the original Fortran instead of translated C sources",
    }
    languages = ["C"]

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    @property
    def extension_properties(self):
        name_mangling = "lower_underscore"
        if self.options.get_safe("use_fortran"):
            name_mangling = self.fortran.mangling.value
            # OpenBLAS explicitly overrides IntelLLVM's Windows default.
            if self.settings.os == "Windows" and self.fortran.compiler == "ifx":
                name_mangling = "lower_no_underscore"
        return {"fortran_name_mangling": name_mangling}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.get_safe("fortran") is None:
            self.options.use_fortran = False
        if self.settings.compiler in ["msvc", "apple-clang"]:
            self.options.build_relapack = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.build_lapack:
            del self.options.build_relapack
            del self.options.use_fortran
        if self.options.threading != "serial":
            del self.options.use_locking
        else:
            del self.options.max_threads
        if self.options.threading != "openmp":
            del self.options.max_omp_parallel
        if not self.options.get_safe("use_fortran", False):
            self.settings.rm_safe("fortran")

        if is_msvc(self) and not self.options.target:
            self.options.target = "GENERIC"

        # When cross-compiling, OpenBLAS requires explicitly setting TARGET
        if cross_building(self, skip_x64_x86=True) and not self.options.target:
            # Try inferring the target from settings.arch
            target = conan_arch_to_openblas_target.get(str(self.settings.arch))
            if target:
                self.output.warning(
                    f"Setting OpenBLAS TARGET={target} based on settings.arch. "
                    "This may result in suboptimal performance. "
                    f'Set the "{self.name}/*:target=XXX" option to silence this warning.'
                )
                self.options.target = target

    def requirements(self):
        if self.options.threading == "openmp":
            self.requires("openmp/system")
        if self.options.get_safe("use_fortran"):
            self.fortran.requires_runtime()

    def validate(self):
        if is_msvc(self) and self.options.target != "GENERIC":
            raise ConanInvalidConfiguration("MSVC only supports OpenBLAS' generic target")
        if self.options.get_safe("build_relapack") and self.settings.compiler in ["msvc", "apple-clang"]:
            # ld: unknown option: --allow-multiple-definition on apple-clang
            raise ConanInvalidConfiguration(f'"{self.name}/*:build_relapack=True" option is only supported for GCC and Clang')
        if self.settings.os == "Android" and self.options.build_lapack:
            if int(self.settings.os.api_level.value) < 23:
                # All basic complex math functions are only available since API level 23.
                raise ConanInvalidConfiguration("build_lapack=True requires Android API level 23 or higher for complex math support")
        if self.options.get_safe("use_fortran"):
            self.fortran.validate_settings()

    def build_requirements(self):
        if self.options.threading == "openmp":
            # Required for LINK_LANGUAGE generator expression
            self.tool_requires("cmake/[>=3.18 <5]")

    def validate_build(self):
        # If we're cross-compiling, and the user didn't provide the target, and
        # we couldn't infer the target from settings.arch, fail
        if cross_building(self, skip_x64_x86=True) and not self.options.target:
            raise ConanInvalidConfiguration(f'Could not determine OpenBLAS TARGET. Please set the "{self.name}/*:target=XXX" option.')
        if self.options.get_safe("use_fortran"):
            self.fortran.validate_build()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Disable test subdirs.
        # ctest also otherwise fails to compile on Android API 22 and earlier due to incomplete complex support.
        save(self, os.path.join(self.source_folder, "cpp_thread_test", "CMakeLists.txt"), "")
        save(self, os.path.join(self.source_folder, "ctest", "CMakeLists.txt"), "")
        save(self, os.path.join(self.source_folder, "test", "CMakeLists.txt"), "")
        save(self, os.path.join(self.source_folder, "utest", "CMakeLists.txt"), "")
        save(self, os.path.join(self.source_folder, "lapack-netlib", "TESTING", "CMakeLists.txt"), "")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_WITHOUT_LAPACK"] = not self.options.build_lapack
        tc.variables["BUILD_RELAPACK"] = self.options.get_safe("build_relapack", False)
        tc.variables["NOFORTRAN"] = not self.options.get_safe("use_fortran", False)
        tc.variables["C_LAPACK"] = not self.options.get_safe("use_fortran", False)
        tc.variables["INTERFACE64"] = self.options.interface == "ilp64"
        tc.variables["USE_THREAD"] = self.options.threading != "serial"
        tc.variables["USE_OPENMP"] = self.options.threading == "openmp"
        tc.variables["USE_LOCKING"] = self.options.get_safe("use_locking", False)
        if self.options.get_safe("max_threads", "auto") != "auto":
            tc.variables["NUM_THREADS"] = self.options.max_threads
        if self.options.get_safe("max_omp_parallel"):
            tc.variables["NUM_PARALLEL"] = self.options.max_omp_parallel
        if self.options.target:
            tc.cache_variables["TARGET"] = self.options.target
        tc.variables["DYNAMIC_ARCH"] = self.options.dynamic_arch
        tc.variables["BUILD_BFLOAT16"] = self.options.build_bfloat16
        tc.variables["MSVC_STATIC_CRT"] = is_msvc_static_runtime(self)
        if is_msvc(self):
            # OpenBLAS declares generic ASM, but its MSVC build has no assembly sources.
            for runtime in ("MultiThreaded", "MultiThreadedDLL", "MultiThreadedDebug", "MultiThreadedDebugDLL"):
                tc.variables[f"CMAKE_ASM_COMPILE_OPTIONS_MSVC_RUNTIME_LIBRARY_{runtime}"] = ""
            tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.variables["ANDROID"] = self.settings.os == "Android"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    @property
    def _lib_name(self):
        name = "openblas"
        if self.options.interface == "ilp64":
            name += "_64"
        if self.options.shared and self.settings.build_type == "Debug" and not is_msvc(self):
            name += "_d"
        return name

    @property
    def _64bit(self):
        return "64" if self.options.interface == "ilp64" else ""

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", f"OpenBLAS{self._64bit}")
        cmake_namespace = f"OpenBLAS{self._64bit}"
        self.cpp_info.set_property("cmake_target_name", f"{cmake_namespace}::OpenBLAS")
        aliases = [f"OpenBLAS::{self.options.threading}"]
        if self.options.interface == "ilp64":
            aliases.extend(["OpenBLAS::OpenBLAS", "OpenBLAS::OpenBLAS64"])
        self.cpp_info.set_property("cmake_target_aliases", aliases)
        self.cpp_info.set_property("pkg_config_name", f"openblas{self._64bit}")

        self.cpp_info.includedirs.append(f"include/openblas{self._64bit}")
        self.cpp_info.libs = [self._lib_name]
        if self.options.build_lapack:
            self.cpp_info.defines.append("HAVE_LAPACK_CONFIG_H")
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs.append("m")
                if self.options.threading != "serial":
                    self.cpp_info.system_libs.append("pthread")
        if self.options.get_safe("use_fortran"):
            self.fortran.add_runtime_to_cpp_info(self.cpp_info)

        self.runenv_info.define_path("OpenBLAS_HOME", self.package_folder)
