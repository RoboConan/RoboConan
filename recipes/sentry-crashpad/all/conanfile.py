import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SentryCrashpadConan(ConanFile):
    name = "sentry-crashpad"
    description = "Crashpad is a crash-reporting system."
    homepage = "https://github.com/getsentry/sentry-native"
    license = "Apache-2.0"
    topics = ("crashpad", "error-reporting", "crash-reporting")
    provides = "crashpad", "mini_chromium"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "with_tls": ["openssl", False],
    }
    default_options = {
        "fPIC": True,
        "with_tls": "openssl",
    }

    @property
    def _is_mingw(self):
        return self.settings.os == "Windows" and self.settings.compiler == "gcc"

    @property
    def _minimum_compilers_version(self):
        return {
            "msvc": "191",
            "gcc": "6",
            "clang": "3.4",
            "apple-clang": "5.1",
        }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os not in ("Linux", "Android"):
            del self.options.with_tls

    def build_requirements(self):
        if self._is_mingw:
            self.tool_requires("jwasm/2.13")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        if self.settings.os in ("Linux", "FreeBSD"):
            self.requires("libcurl/[>=7.78.0 <9]")
        if self.options.get_safe("with_tls"):
            self.requires("openssl/[<5]")

    def validate(self):
        # Set as required in crashpad CMake file.
        # See https://github.com/getsentry/crashpad/blob/71bcaad4cf30294b8de1bfa02064ab629437163b/CMakeLists.txt#L67
        check_min_cppstd(self, 14)

        minimum_version = self._minimum_compilers_version.get(str(self.settings.compiler), False)
        if not minimum_version:
            self.output.warning("Compiler is unknown. Assuming it supports C++14.")
        elif Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(f"Build requires support for C++14. Minimum version for {self.settings.compiler} is {minimum_version}")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)])
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CRASHPAD_ENABLE_INSTALL"] = True
        tc.variables["CRASHPAD_ENABLE_INSTALL_DEV"] = True
        tc.variables["CRASHPAD_ZLIB_SYSTEM"] = True
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        openssl_repl = "find_package(OpenSSL REQUIRED)" if self.options.get_safe("with_tls") else ""
        if Version(self.version) < "0.6.1":
            replace_in_file(self, os.path.join(self.source_folder, "external", "crashpad", "CMakeLists.txt"),
                            "find_package(OpenSSL)", openssl_repl)
        cmake = CMake(self)
        cmake.configure(build_script_folder="external/crashpad")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "external", "crashpad"),
                              dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.configure(build_script_folder="external/crashpad")
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "crashpad")

        # mini_chromium
        self.cpp_info.components["crashpad_mini_chromium"].set_property("cmake_target_name", "crashpad::mini_chromium")
        self.cpp_info.components["crashpad_mini_chromium"].includedirs.append(os.path.join("include", "crashpad", "mini_chromium"))
        self.cpp_info.components["crashpad_mini_chromium"].libs = ["mini_chromium"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.components["crashpad_mini_chromium"].system_libs.append("pthread")
        elif is_apple_os(self):
            self.cpp_info.components["crashpad_mini_chromium"].frameworks = ["CoreFoundation", "Foundation", "Security"]
            if self.settings.os == "Macos":
                self.cpp_info.components["crashpad_mini_chromium"].frameworks.extend(["ApplicationServices", "IOKit"])
            else:  # iOS
                self.cpp_info.components["crashpad_mini_chromium"].frameworks.extend(["CoreGraphics", "CoreText"])

        # compat
        self.cpp_info.components["crashpad_compat"].set_property("cmake_target_name", "crashpad::compat")
        self.cpp_info.components["crashpad_compat"].includedirs.append(os.path.join("include", "crashpad"))
        # On Apple crashpad_compat is an interface library
        if not is_apple_os(self):
            self.cpp_info.components["crashpad_compat"].libs = ["crashpad_compat"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.components["crashpad_compat"].system_libs.append("dl")

        # util
        self.cpp_info.components["crashpad_util"].set_property("cmake_target_name", "crashpad::util")
        self.cpp_info.components["crashpad_util"].libs = ["crashpad_util"]
        self.cpp_info.components["crashpad_util"].requires = ["crashpad_compat", "crashpad_mini_chromium", "zlib-ng::zlib-ng"]
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.components["crashpad_util"].system_libs.extend(["pthread", "rt"])
            # Requires libcurl https://github.com/getsentry/crashpad/blob/2237d97ee2c38c930c07001e660be57324f69a37/util/CMakeLists.txt#L256
            self.cpp_info.components["crashpad_util"].requires.extend(["libcurl::libcurl"])
        elif self.settings.os == "Windows":
            self.cpp_info.components["crashpad_util"].system_libs.append("winhttp")
        elif self.settings.os == "Macos":
            self.cpp_info.components["crashpad_util"].frameworks.extend(["CoreFoundation", "Foundation", "IOKit"])
            self.cpp_info.components["crashpad_util"].system_libs.append("bsm")
        if self.options.get_safe("with_tls") == "openssl":
            self.cpp_info.components["crashpad_util"].requires.append("openssl::openssl")

        # client
        self.cpp_info.components["crashpad_client"].set_property("cmake_target_name", "crashpad::client")
        self.cpp_info.components["crashpad_client"].libs = ["crashpad_client"]
        self.cpp_info.components["crashpad_client"].requires = ["crashpad_util", "crashpad_mini_chromium"]

        # snapshot
        self.cpp_info.components["crashpad_snapshot"].set_property("cmake_target_name", "crashpad::snapshot")
        self.cpp_info.components["crashpad_snapshot"].libs = ["crashpad_snapshot"]
        self.cpp_info.components["crashpad_snapshot"].requires = [
            "crashpad_client", "crashpad_compat",
            "crashpad_util", "crashpad_mini_chromium",
        ]
        if self.settings.os == "Windows":
            self.cpp_info.components["snapshot"].system_libs.append("powrprof")

        # minidump
        self.cpp_info.components["crashpad_minidump"].set_property("cmake_target_name", "crashpad::minidump")
        self.cpp_info.components["crashpad_minidump"].libs = ["crashpad_minidump"]
        self.cpp_info.components["crashpad_minidump"].requires = [
            "crashpad_compat", "crashpad_snapshot",
            "crashpad_util", "crashpad_mini_chromium",
        ]

        if self.settings.os == "Windows":
            # getopt
            self.cpp_info.components["crashpad_getopt"].set_property("cmake_target_name", "crashpad::getopt")
            self.cpp_info.components["crashpad_getopt"].libs = ["crashpad_getopt"]

        # handler
        self.cpp_info.components["crashpad_handler"].set_property("cmake_target_name", "crashpad::handler")
        self.cpp_info.components["crashpad_handler"].libs = ["crashpad_handler_lib"]
        self.cpp_info.components["crashpad_handler"].requires = [
            "crashpad_compat", "crashpad_minidump", "crashpad_snapshot",
            "crashpad_util", "crashpad_mini_chromium",
        ]
        if self.settings.os == "Windows":
            self.cpp_info.components["crashpad_handler"].requires.append("crashpad_getopt")

        # tools
        self.cpp_info.components["crashpad_tools"].set_property("cmake_target_name", "crashpad::tools")
        self.cpp_info.components["crashpad_tools"].libs = ["crashpad_tools"]
