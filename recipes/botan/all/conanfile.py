import os
import shutil
from functools import cached_property

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name, XCRun
from conan.tools.build import build_jobs, check_min_cppstd, check_max_cppstd
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, VCVars, unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class BotanConan(ConanFile):
    name = "botan"
    description = "Botan is a cryptography library written in modern C++."
    license = "BSD-2-Clause"
    homepage = "https://github.com/randombit/botan"
    topics = ("cryptography", "crypto", "c++11", "c++20", "tls")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "amalgamation": [True, False],
        "with_bzip2": [True, False],
        "with_sqlite3": [True, False],
        "with_zlib": [True, False],
        "with_boost": [True, False],
        "with_sse2": [True, False],
        "with_ssse3": [True, False],
        "with_sse4_1": [True, False],
        "with_sse4_2": [True, False],
        "with_avx2": [True, False],
        "with_bmi2": [True, False],
        "with_rdrand": [True, False],
        "with_rdseed": [True, False],
        "with_aes_ni": [True, False],
        "with_sha_ni": [True, False],
        "with_altivec": [True, False],
        "with_neon": [True, False],
        "with_armv8crypto": [True, False],
        "with_powercrypto": [True, False],
        "enable_modules": [None, "ANY"],
        "disable_modules": [None, "ANY"],
        "enable_experimental_features": [True, False],
        "enable_deprecated_features": [True, False],
        "system_cert_bundle": [None, "ANY"],
        "module_policy": [None, "bsi", "modern", "nist"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "amalgamation": False,
        "with_bzip2": False,
        "with_sqlite3": False,
        "with_zlib": False,
        "with_boost": False,
        "with_sse2": True,
        "with_ssse3": True,
        "with_sse4_1": True,
        "with_sse4_2": True,
        "with_avx2": True,
        "with_bmi2": True,
        "with_rdrand": True,
        "with_rdseed": True,
        "with_aes_ni": True,
        "with_sha_ni": True,
        "with_altivec": True,
        "with_neon": True,
        "with_armv8crypto": True,
        "with_powercrypto": True,
        "enable_modules": None,
        "disable_modules": None,
        "enable_experimental_features": False,
        "enable_deprecated_features": True,
        "system_cert_bundle": None,
        "module_policy": None,
    }

    @cached_property
    def _is_x86(self):
        return str(self.settings.arch) in ["x86", "x86_64"]

    @cached_property
    def _is_ppc(self):
        return "ppc" in str(self.settings.arch)

    @cached_property
    def _is_arm(self):
        return "arm" in str(self.settings.arch)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not self._is_x86:
            del self.options.with_sse2
            del self.options.with_ssse3
            del self.options.with_sse4_1
            del self.options.with_sse4_2
            del self.options.with_avx2
            del self.options.with_bmi2
            del self.options.with_rdrand
            del self.options.with_rdseed
            del self.options.with_aes_ni
            del self.options.with_sha_ni
        if not self._is_arm:
            del self.options.with_neon
            del self.options.with_armv8crypto
        if not self._is_ppc:
            del self.options.with_altivec
            del self.options.with_powercrypto

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        if self.options.with_bzip2:
            self.requires("bzip2/[^1.0.8]")
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_sqlite3:
            self.requires("sqlite3/[>=3.45.0 <4]")
        if self.options.with_boost:
            self.requires("boost/[^1.74.0]", options={"with_coroutine": True})

    @property
    def _min_cppstd(self):
        # From the same links as below
        return 11 if Version(self.version) < "3.0.0" else 20

    @property
    def _compilers_minimum_version(self):
        if Version(self.version).major < 3:
            # From https://github.com/randombit/botan/blob/2.19.3/doc/support.rst
            return {
                "gcc": "4.8",
                "clang": "3.5",
                "msvc": "190",
            }
        else:
            # From https://github.com/randombit/botan/blob/master/doc/support.rst
            return {
                "gcc":  "11.2",
                "clang": "14",
                "apple-clang": "14",
                "msvc": "193",
            }

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)
        if Version(self.version) < 3:
            # Uses std::result_of, which is removed in C++20
            check_max_cppstd(self, 17)

        def lazy_lt_semver(v1, v2):
            return all(int(p1) < int(p2) for p1, p2 in zip(str(v1).split("."), str(v2).split(".")))

        compiler = self.settings.compiler
        compiler_name = str(compiler)
        compiler_version = Version(compiler.version)
        minimum_version = self._compilers_minimum_version.get(compiler_name, False)
        if minimum_version and lazy_lt_semver(compiler_version, minimum_version):
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support (minimum {compiler_name} {minimum_version})."
            )

        if self.settings.compiler == "clang" and self.settings.os == "Linux" and self.settings.compiler.libcxx not in ["libstdc++11", "libc++"]:
            raise ConanInvalidConfiguration(
                'Using Botan with Clang on Linux requires either "compiler.libcxx=libstdc++11" '
                'or "compiler.libcxx=libc++"')

        # Some older compilers cannot handle the amalgamated build anymore
        # See also https://github.com/randombit/botan/issues/2328
        if self.options.amalgamation:
            if (self.settings.compiler == "apple-clang" and compiler_version < "10") or \
               (self.settings.compiler == "gcc" and compiler_version < "8") or \
               (self.settings.compiler == "clang" and compiler_version < "7"):
                raise ConanInvalidConfiguration(
                    f"botan amalgamation is not supported for {compiler}/{compiler_version}")

        if Version(self.version) >= "3.9":
            # Botan 3.9 removed support for disabling the usage of specific ISAs via configure.py switches.
            # See: https://github.com/randombit/botan/pull/4927
            #
            # TODO: Eventually, we should remove these Conan options entirely (latest with Botan4).
            isa_opts = ["with_sse2", "with_ssse3", "with_sse4_1", "with_sse4_2", "with_avx2", "with_bmi2",
                        "with_rdrand", "with_rdseed", "with_aes_ni", "with_sha_ni", "with_altivec", "with_neon",
                        "with_armv8crypto", "with_powercrypto"]
            if any(not self.options.get_safe(opt, True) for opt in isa_opts):
                raise ConanInvalidConfiguration(
                    "Since Botan 3.9 users are expected to explicitly disable modules that use a certain ISA. "
                    "See https://botan.randombit.net/doxygen/topics.html for a list of available modules.\nUse "
                    "the Conan option disable_modules=... with a comma-separated list of module names instead of "
                    f"disabling any of those now-deprecated Conan options: {', '.join(isa_opts)}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @cached_property
    def _cxxflags(self):
        return AutotoolsToolchain(self).vars().get("CXXFLAGS")

    @cached_property
    def _is_mingw(self):
        return self.settings.os == "Windows" and self.settings.compiler == "gcc"

    @property
    def _botan_os(self):
        if self._is_mingw:
            return "mingw"
        return {"Windows": "windows",
                "Linux": "linux",
                "Macos": "darwin",
                "Android": "android",
                "baremetal": "none",
                "iOS": "ios"}.get(str(self.settings.os))

    def _dependency_build_flags(self, dependency):
        # Since botan has a custom build system, we need to specifically inject
        # these build parameters so that it picks up the correct dependencies.
        dep_cpp_info = self.dependencies[dependency].cpp_info
        return \
            [f"--with-external-includedir={include_path}" for include_path in dep_cpp_info.includedirs] + \
            [f"--with-external-libdir={lib_path}" for lib_path in dep_cpp_info.libdirs] + \
            [f"--define-build-macro={define}" for define in dep_cpp_info.defines]

    @property
    def _configure_cmd(self):
        botan_compiler = {
            "apple-clang": "clang",
            "clang": "clang",
            "gcc": "gcc",
            "msvc": "msvc",
            "Visual Studio": "msvc",
            "intel-cc": "icc",
            "sun-cc": "sunstudio",
        }[str(self.settings.compiler)]

        abi_flags = []
        extra_cxx_flags = []
        build_flags = []

        if self._is_linux_clang_libcxx:
            abi_flags.extend(["-stdlib=libc++", "-lc++abi"])

        if self.settings.compiler in ["clang", "apple-clang", "gcc"]:
            if self.settings.arch == "x86":
                abi_flags.append("-m32")
            elif self.settings.arch == "x86_64":
                abi_flags.append("-m64")

        if self.settings.compiler in ["apple-clang"]:
            if self.settings.arch in ["armv7"]:
                abi_flags.append("-arch armv7")
            elif self.settings.arch in ["armv8"]:
                abi_flags.append("-arch arm64")
            elif self.settings.arch in ["x86_64"]:
                abi_flags.append("-arch x86_64")

        if self.options.get_safe("fPIC", True) and not is_msvc(self):
            extra_cxx_flags.append("-fPIC")

        if is_apple_os(self):
            if self.settings.get_safe("os.version"):
                # Required, see https://github.com/conan-io/conan-center-index/pull/3456
                extra_cxx_flags.append(AutotoolsToolchain(self).apple_min_version_flag)
            macos_sdk_path = f"-isysroot {XCRun(self).sdk_path}"
            extra_cxx_flags.append(macos_sdk_path)

        if self._cxxflags:
            extra_cxx_flags.append(self._cxxflags)

        if Version(self.version) >= "3.4":
            # Botan 3.4.0 introduced a "module life cycle" feature, before that
            # the experimental/deprecated feature switches are ignored.
            if self.options.enable_experimental_features:
                build_flags.append("--enable-experimental-features")
            else:
                build_flags.append("--disable-experimental-features")
            if self.options.enable_deprecated_features:
                build_flags.append("--enable-deprecated-features")
            else:
                build_flags.append("--disable-deprecated-features")

        if self.options.enable_modules:
            build_flags.append("--minimized-build")
            build_flags.append(f"--enable-modules={self.options.enable_modules}")

        if self.options.disable_modules:
            build_flags.append(f"--disable-modules={self.options.disable_modules}")

        cxx = AutotoolsToolchain(self).vars().get("CXX")
        if cxx:
            build_flags.append(f'--cc-bin="{cxx}"')

        if self.options.amalgamation:
            build_flags.append("--amalgamation")

        if self.options.system_cert_bundle:
            build_flags.append(f"--system-cert-bundle={self.options.system_cert_bundle}")

        sysroot = self.conf.get("tools.build:sysroot")
        if sysroot:
            build_flags.append(f'--with-sysroot-dir="{sysroot}"')

        if self.options.with_bzip2:
            build_flags.append("--with-bzip2")
            build_flags.extend(self._dependency_build_flags("bzip2"))
        if self.options.with_sqlite3:
            build_flags.append("--with-sqlite3")
            build_flags.extend(self._dependency_build_flags("sqlite3"))
        if self.options.with_zlib:
            build_flags.append("--with-zlib")
            build_flags.extend(self._dependency_build_flags("zlib-ng"))
        if self.options.with_boost:
            build_flags.append("--with-boost")
            build_flags.extend(self._dependency_build_flags("boost"))

        if self.options.module_policy:
            build_flags.append(f"--module-policy={self.options.module_policy}")

        if self._is_x86 and Version(self.version) < "3.9":
            if not self.options.with_sse2:
                build_flags.append("--disable-sse2")
            if not self.options.with_ssse3:
                build_flags.append("--disable-ssse3")
            if not self.options.with_sse4_1:
                build_flags.append("--disable-sse4.1")
            if not self.options.with_sse4_2:
                build_flags.append("--disable-sse4.2")
            if not self.options.with_avx2:
                build_flags.append("--disable-avx2")
            if not self.options.with_bmi2:
                build_flags.append("--disable-bmi2")
            if not self.options.with_rdrand:
                build_flags.append("--disable-rdrand")
            if not self.options.with_rdseed:
                build_flags.append("--disable-rdseed")
            if not self.options.with_aes_ni:
                build_flags.append("--disable-aes-ni")
            if not self.options.with_sha_ni:
                build_flags.append("--disable-sha-ni")

        if self._is_ppc and Version(self.version) < "3.9":
            if not self.options.with_powercrypto:
                build_flags.append("--disable-powercrypto")
            if not self.options.with_altivec:
                build_flags.append("--disable-altivec")

        if self._is_arm and Version(self.version) < "3.9":
            if not self.options.with_neon:
                build_flags.append("--disable-neon")
            if not self.options.with_armv8crypto:
                build_flags.append("--disable-armv8crypto")

        if self.settings.build_type == "Debug":
            build_flags.append("--debug-mode")
        elif self.settings.build_type == "RelWithDebInfo":
            build_flags.append("--with-debug-info")

        build_targets = ["shared" if self.options.shared else "static"]

        if self._is_mingw:
            build_flags.append("--without-stack-protector")

        if is_msvc(self):
            build_flags.append(f"--msvc-runtime={msvc_runtime_flag(self)}")

        build_flags.append("--without-pkg-config")

        call_python = "python" if self.settings.os == "Windows" else ""

        prefix = unix_path(self, self.package_folder) if self._is_mingw else self.package_folder

        botan_abi = " ".join(abi_flags) if abi_flags else " "
        botan_cxx_extras = " ".join(extra_cxx_flags) if extra_cxx_flags else " "

        configure_cmd = (f'{call_python} ./configure.py'
                         f' --build-targets={",".join(build_targets)}'
                         f' --distribution-info="Conan"'
                         f' --without-documentation'
                         f' --cc-abi-flags="{botan_abi}"'
                         f' --extra-cxxflags="{botan_cxx_extras}"'
                         f' --cc={botan_compiler}'
                         f' --cpu={self.settings.arch}'
                         f' --prefix="{prefix}"'
                         f' --os={self._botan_os}'
                         f' {" ".join(build_flags)}')

        return configure_cmd

    @property
    def _make_cmd(self):
        return "nmake" if is_msvc(self) else self._gnumake_cmd

    @cached_property
    def _make_program(self):
        return self.conf.get("tools.gnu:make_program", shutil.which("make") or shutil.which("mingw32-make"))

    @property
    def _gnumake_cmd(self):
        make_ldflags = "LDFLAGS=-lc++abi" if self._is_linux_clang_libcxx else ""
        make_cmd = f"{make_ldflags} {self._make_program} -j{build_jobs(self)}"
        return make_cmd

    @property
    def _make_install_cmd(self):
        if is_msvc(self):
            return "nmake install"
        return f"{self._make_program} install"

    @property
    def _is_linux_clang_libcxx(self):
        return (
            self.settings.os == "Linux" and
            self.settings.compiler == "clang" and
            self.settings.compiler.libcxx == "libc++"
        )

    def generate(self):
        if is_msvc(self):
            VCVars(self).generate()

        # This is to work around botan's configure script that *replaces* its
        # standard (platform dependent) flags in presence of an environment
        # variable ${CXXFLAGS}. Most notably, this would build botan with
        # disabled compiler optimizations.
        self.buildenv.unset("CXXFLAGS")
        VirtualBuildEnv(self).generate()

    def build(self):
        with chdir(self, self.source_folder):
            self.run(self._configure_cmd)
            self.run(self._make_cmd)

    def package(self):
        copy(self, "license.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        with chdir(self, self.source_folder):
            self.run(self._make_install_cmd)
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "botan")
        self.cpp_info.set_property("cmake_target_name", "botan::botan")
        self.cpp_info.set_property("cmake_target_aliases", [
            "botan::botan-static",
            "Botan::Botan", "Botan::Botan-static",  # set for backwards compatibility
        ])
        major = Version(self.version).major
        self.cpp_info.set_property("pkg_config_name", f"botan-{major}")
        self.cpp_info.libs = [f"botan-{major}" if major >= 3 or not is_msvc(self) else "botan"]
        self.cpp_info.includedirs = [f"include/botan-{major}"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["dl", "rt", "pthread", "m"]
        if self.settings.os == "Macos":
            self.cpp_info.frameworks = ["Security", "CoreFoundation"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "crypt32"]
