import fnmatch
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import build_jobs
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.21" # for cmake_extra_variables


_OPENSSL_FEATURES = (
    "aria", "apps", "autoload_config", "asm", "async", "blake2", "bf",
    "camellia", "chacha", "cms", "comp", "ct", "cast", "deprecated", "des",
    "dgram", "dh", "dsa", "dso", "ec", "ecdh", "ecdsa", "ech", "filenames", "fips",
    "gost", "hmac_drbg_kdf", "idea", "kbkdf", "krb5kdf", "legacy", "md2", "md4", "mdc2", "module", "ocsp",
    "pinshared", "rc2", "rc4", "rc5", "rfc3779", "rmd160", "sm2", "sm3", "sm4",
    "pvkkdf", "srp", "srtp", "srtpkdf", "sse2", "sshkdf", "sskdf", "stdio", "seed",
    "snmpkdf", "sock", "threads", "tls1", "ts", "whirlpool", "x942kdf", "x963kdf",
)

_OPENSSL_DISABLED_BY_DEFAULT_FEATURES = ("ec_explicit_curves",)


class OpenSSLConan(ConanFile):
    name = "openssl"
    homepage = "https://github.com/openssl/openssl"
    license = "Apache-2.0"
    topics = ("ssl", "tls", "encryption", "security")
    description = "A toolkit for the Transport Layer Security (TLS) and Secure Sockets Layer (SSL) protocols"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_weak_ssl_ciphers": [True, False],
        "386": [True, False],
        "enable_trace": [True, False],
        **{feature: [True, False] for feature in _OPENSSL_FEATURES},
        **{feature: [True, False] for feature in _OPENSSL_DISABLED_BY_DEFAULT_FEATURES},
        "with_zlib": [True, False],
        "with_brotli": [True, False],
        "with_zstd": [True, False],
        "openssldir": [None, "ANY"],
        "tls_security_level": [None, 0, 1, 2, 3, 4, 5],
        "extra_build_opts": [None, "ANY"],
    }
    default_options = {key: True for key in options}
    default_options["shared"] = False
    default_options["fPIC"] = True
    default_options["enable_weak_ssl_ciphers"] = False
    default_options["386"] = False
    default_options["enable_trace"] = False
    default_options["ec_explicit_curves"] = False
    default_options["with_brotli"] = False
    default_options["with_zstd"] = False
    default_options["openssldir"] = None
    default_options["tls_security_level"] = None
    default_options["extra_build_opts"] = None

    @property
    def _is_mingw(self):
        is_gcc = self.settings.compiler == "gcc"
        is_clang = self.settings.compiler == "clang" and self.settings.compiler.get_safe("runtime") is None
        return self.settings.os == "Windows" and (is_gcc or is_clang)

    @property
    def _msvc_abi(self):
        return self.settings.os == "Windows" and self.settings.compiler.get_safe("runtime")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_brotli:
            self.requires("brotli/[^1.1]")
        if self.options.with_zstd:
            self.requires("zstd/[~1.5]")

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            if self.options.asm and self.settings.arch in ("x86", "x86_64"):
                self.tool_requires("nasm/[*]")
            if self._msvc_abi:
                self.tool_requires("jom/[*]")
                self.tool_requires("strawberryperl/[^5.32.1.1]")
            else:
                self.win_bash = True
                if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                    self.tool_requires("msys2/latest")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    @property
    def _target(self):
        custom_target = self.conf.get("user.openssl:target", check_type=str)
        if custom_target:
            return custom_target

        if self.settings.os == "Windows" and self._is_mingw:
            return {
                "x86": "mingw",
                "x86_64": "mingw64",
                "armv8": "mingwarm64",
            }.get(str(self.settings.arch)) or self._unsupported_target()

        compiler = "Visual Studio" if is_msvc(self) else str(self.settings.compiler)
        query = f"{self.settings.os}-{self.settings.arch}-{compiler}"
        targets = {
            "Linux-x86-clang": "linux-x86-clang",
            "Linux-x86_64-clang": "linux-x86_64-clang",
            "Linux-x86-*": "linux-x86",
            "Linux-x86_64-*": "linux-x86_64",
            "Linux-armv4-*": "linux-armv4",
            "Linux-armv4i-*": "linux-armv4",
            "Linux-armv5el-*": "linux-armv4",
            "Linux-armv5hf-*": "linux-armv4",
            "Linux-armv6-*": "linux-armv4",
            "Linux-armv7-*": "linux-armv4",
            "Linux-armv7hf-*": "linux-armv4",
            "Linux-armv7s-*": "linux-armv4",
            "Linux-armv7k-*": "linux-armv4",
            "Linux-armv8-*": "linux-aarch64",
            "Linux-armv8.3-*": "linux-aarch64",
            "Linux-armv8_32-*": "linux-arm64ilp32",
            "Linux-mips-*": "linux-mips32",
            "Linux-mips64-*": "linux-mips64",
            "Linux-ppc32-*": "linux-ppc",
            "Linux-ppc32be-*": "linux-ppc",
            "Linux-ppc64-*": "linux-ppc64",
            "Linux-ppc64le-*": "linux-ppc64le",
            "Linux-s390x-*": "linux64-s390x",
            "Linux-riscv32-*": "linux32-riscv32",
            "Linux-riscv64-*": "linux64-riscv64",
            "Linux-e2k-*-*": "linux-generic64",
            "Linux-sparc-*": "linux-sparcv8",
            "Linux-sparcv9-*": "linux64-sparcv9",
            "Macos-x86_64-*": "darwin64-x86_64-cc",
            "Macos-armv8-*": "darwin64-arm64-cc",
            "iOS-x86_64-*": "iossimulator-x86_64-xcrun",
            "iOS-armv8-*": "ios64-xcrun",
            "watchOS-*-*": "iphoneos-cross",
            "tvOS-*-*": "iphoneos-cross",
            "Android-armv7-*": "android-arm",
            "Android-armv7hf-*": "android-arm",
            "Android-armv8-*": "android-arm64",
            "Android-x86-*": "android-x86",
            "Android-x86_64-*": "android-x86_64",
            "Android-mips-*": "android-mips",
            "Android-mips64-*": "android-mips64",
            "Android-riscv64-*": "android-riscv64",
            "Windows-x86-Visual Studio": "VC-WIN32",
            "Windows-x86_64-Visual Studio": "VC-WIN64A",
            "Windows-armv7-Visual Studio": "VC-WIN32-ARM",
            "Windows-armv8-Visual Studio": "VC-WIN64-CLANGASM-ARM",
            "Windows-x86-clang": "VC-WIN32",
            "Windows-x86_64-clang": "VC-WIN64A",
            "Windows-armv7-clang": "VC-WIN32-ARM",
            "Windows-armv8-clang": "VC-CLANG-WIN64-CLANGASM-ARM",
            "WindowsStore-x86-*": "VC-WIN32-UWP",
            "WindowsStore-x86_64-*": "VC-WIN64A-UWP",
            "WindowsStore-armv7-*": "VC-WIN32-ARM-UWP",
            "WindowsStore-armv8-*": "VC-WIN64-ARM-UWP",
            "WindowsCE-*-*": "VC-CE",
            "SunOS-x86-gcc": "solaris-x86-gcc",
            "SunOS-x86_64-gcc": "solaris64-x86_64-gcc",
            "SunOS-x86_64-suncc": "solaris64-x86_64-cc",
            "SunOS-sparc-gcc": "solaris-sparcv8-gcc",
            "SunOS-sparcv9-gcc": "solaris64-sparcv9-gcc",
            "SunOS-sparc-suncc": "solaris-sparcv8-cc",
            "SunOS-sparcv9-suncc": "solaris64-sparcv9-cc",
            "FreeBSD-x86-*": "BSD-x86",
            "FreeBSD-x86_64-*": "BSD-x86_64",
            "FreeBSD-armv7-*": "BSD-armv4",
            "FreeBSD-armv8-*": "BSD-aarch64",
            "FreeBSD-ppc32-*": "BSD-ppc",
            "FreeBSD-ppc32be-*": "BSD-ppc",
            "FreeBSD-ppc64-*": "BSD-ppc64",
            "FreeBSD-ppc64le-*": "BSD-ppc64le",
            "FreeBSD-riscv32-*": "BSD-riscv32",
            "FreeBSD-riscv64-*": "BSD-riscv64",
            "FreeBSD-sparc-*": "BSD-sparcv8",
            "FreeBSD-sparcv9-*": "BSD-sparc64",
            "AIX-ppc32-gcc": "aix-gcc",
            "AIX-ppc64-gcc": "aix64-gcc",
            "AIX-ppc32-clang": "aix-clang",
            "AIX-ppc64-clang": "aix64-clang",
            "AIX-ppc32-*": "aix-cc",
            "AIX-ppc64-*": "aix64-cc",
            "Emscripten-*-*": "cc",
            "Neutrino-*-*": "cc",
        }
        target = next((value for pattern, value in targets.items() if fnmatch.fnmatch(query, pattern)), None)
        return target or self._unsupported_target()

    def _unsupported_target(self):
        raise ConanInvalidConfiguration(
            f"Unable to map the OpenSSL configuration for "
            f"{self.settings.os}/{self.settings.arch}/{self.settings.compiler}. "
            "Set user.openssl:target to an OpenSSL Configure target."
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        if is_msvc(self):
            tc.extra_cflags.append("-nologo")
        if is_apple_os(self) and self.options.shared:
            tc.extra_ldflags.append("-headerpad_max_install_names")
        tc.generate()

    def _adjust_path(self, path):
        if self._msvc_abi:
            return path.replace("\\", "/")
        return unix_path(self, path)

    @property
    def _configure_args(self):
        openssldir = self.options.openssldir or "/etc/ssl"
        if self.win_bash:
            openssldir = unix_path(self, openssldir)
        args = [
            f'"{self._target}"',
            "shared" if self.options.shared else "no-shared",
            "--debug" if self.settings.build_type == "Debug" else "--release",
            "--prefix=C:/" if self._msvc_abi else "--prefix=/",
            "--libdir=lib",
            f'--openssldir="{openssldir}"',
            "no-docs",
            "no-unit-test",
            "no-tests",
        ]

        if self.settings.os == "Android":
            args.append(f"-D__ANDROID_API__={self.settings.os.api_level}")
        if self.settings.get_safe("compiler.runtime") == "static":
            args.append("enable-static-vcruntime")
        if self.settings.os != "Windows":
            args.append("-fPIC" if self.options.get_safe("fPIC", True) else "no-pic")

        if str(self.options.tls_security_level) != "None":
            args.append(f"-DOPENSSL_TLS_SECURITY_LEVEL={self.options.tls_security_level}")

        if self.options.with_zlib:
            zlib_cpp_info = self.dependencies["zlib-ng"].cpp_info.aggregated_components()
            include_path = self._adjust_path(zlib_cpp_info.includedirs[0])
            if self._msvc_abi:
                zlib_lib = self._adjust_path(
                    os.path.join(zlib_cpp_info.libdirs[0], f"{zlib_cpp_info.libs[0]}.lib")
                )
            else:
                zlib_lib = self._adjust_path(zlib_cpp_info.libdirs[0])
            args.extend([
                "zlib",
                f'--with-zlib-include="{include_path}"',
                f'--with-zlib-lib="{zlib_lib}"',
            ])
        else:
            args.append("no-zlib")

        if self.options.with_brotli:
            brotli_cpp_info = self.dependencies["brotli"].cpp_info.aggregated_components()
            args.extend([
                "enable-brotli",
                f'--with-brotli-include="{self._adjust_path(brotli_cpp_info.includedirs[0])}"',
                f'--with-brotli-lib="{self._adjust_path(brotli_cpp_info.libdirs[0])}"',
            ])

        if self.options.with_zstd:
            zstd_cpp_info = self.dependencies["zstd"].cpp_info.aggregated_components()
            zstd_lib = self._adjust_path(zstd_cpp_info.libdirs[0])
            if self._msvc_abi:
                zstd_lib = self._adjust_path(
                    os.path.join(zstd_cpp_info.libdirs[0], f"{zstd_cpp_info.libs[0]}.lib")
                )
            args.extend([
                "enable-zstd",
                f'--with-zstd-include="{self._adjust_path(zstd_cpp_info.includedirs[0])}"',
                f'--with-zstd-lib="{zstd_lib}"',
            ])

        for feature in _OPENSSL_FEATURES:
            if not getattr(self.options, feature):
                args.append(f"no-{feature.replace('_', '-')}")

        for feature in _OPENSSL_DISABLED_BY_DEFAULT_FEATURES:
            if getattr(self.options, feature):
                args.append(f"enable-{feature}")

        for option_name in ("386", "enable_weak_ssl_ciphers", "enable_trace"):
            if getattr(self.options, option_name):
                args.append(option_name.replace("_", "-"))
        if self.options.extra_build_opts:
            args.extend(option.strip() for option in str(self.options.extra_build_opts).split(",") if option.strip())

        return args

    @property
    def _make_program(self):
        if self._msvc_abi:
            return "jom"
        return self.conf.get("tools.gnu:make_program", default="make")

    @property
    def _perl(self):
        return "perl" if "strawberryperl" in self.dependencies.build else ""

    def build(self):
        configure = os.path.join(self.source_folder, "Configure").replace("\\", "/")
        self.run(f'{self._perl} "{configure}" {" ".join(self._configure_args)}', env="conanbuild")
        self.run(f"{self._perl} ./configdata.pm --dump", env="conanbuild")
        self.run(f"{self._make_program} -j{build_jobs(self)}", env="conanbuild")
        if self._msvc_abi:
            replace_in_file(self, "Makefile", "INSTALLTOP_dir=\\", "INSTALLTOP_dir=/")
        if not self._msvc_abi and self.options.shared:
            replace_in_file(self, "Makefile", "INSTALL_LIBS=libcrypto.a libssl.a", "INSTALL_LIBS=")

    def package(self):
        copy(self, "*LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        package_folder = self.package_folder.replace("\\", "/")
        self.run(f'{self._make_program} install_sw -j1 DESTDIR="{package_folder}"', env="conanbuild")
        if is_apple_os(self):
            fix_apple_shared_install_name(self)

        rm(self, "*.pdb", self.package_folder, "lib")
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenSSL")
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("pkg_config_name", "openssl")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["OPENSSL"])
        self.cpp_info.set_property("cmake_extra_variables", {
            "OPENSSL_FOUND": True,
            "OPENSSL_VERSION": self.version,
            "OPENSSL_CRYPTO_LIBRARY": "OpenSSL::Crypto",
            "OPENSSL_CRYPTO_LIBRARIES": "OpenSSL::Crypto",
            "OPENSSL_SSL_LIBRARY": "OpenSSL::SSL",
            "OPENSSL_SSL_LIBRARIES": "OpenSSL::SSL",
            "OPENSSL_LIBRARIES": "OpenSSL::SSL;OpenSSL::Crypto",
        })

        prefix = "lib" if self._msvc_abi else ""
        self.cpp_info.components["ssl"].libs = [f"{prefix}ssl"]
        self.cpp_info.components["crypto"].libs = [f"{prefix}crypto"]
        self.cpp_info.components["ssl"].requires = ["crypto"]

        if self.options.with_zlib:
            self.cpp_info.components["crypto"].requires.append("zlib-ng::zlib-ng")
        if self.options.with_brotli:
            self.cpp_info.components["crypto"].requires.extend([
                "brotli::brotlienc",
                "brotli::brotlidec",
            ])
        if self.options.with_zstd:
            self.cpp_info.components["crypto"].requires.append("zstd::zstd")

        if self.settings.os == "Windows":
            self.cpp_info.components["crypto"].system_libs.extend(["crypt32", "ws2_32", "advapi32", "user32", "bcrypt"])
        elif self.settings.os == "Linux":
            self.cpp_info.components["crypto"].system_libs.append("dl")
            if self.options.threads:
                self.cpp_info.components["crypto"].system_libs.append("pthread")
        elif self.settings.os == "FreeBSD" and self.options.threads:
            self.cpp_info.components["crypto"].system_libs.append("pthread")

        self.cpp_info.components["crypto"].set_property("cmake_target_name", "OpenSSL::Crypto")
        self.cpp_info.components["crypto"].set_property("pkg_config_name", "libcrypto")
        self.cpp_info.components["ssl"].set_property("cmake_target_name", "OpenSSL::SSL")
        self.cpp_info.components["ssl"].set_property("pkg_config_name", "libssl")

        self.runenv_info.define_path("OPENSSL_MODULES", os.path.join(self.package_folder, "lib", "ossl-modules"))
