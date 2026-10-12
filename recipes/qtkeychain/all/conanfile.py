import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps

required_conan_version = ">=2.1"


class QtKeychainConan(ConanFile):
    name = "qtkeychain"
    license = "BSD-3-Clause"
    description = "Platform-independent Qt API for storing passwords securely."
    homepage = "https://github.com/frankosterfeld/qtkeychain"
    topics = ("qt", "keychain")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_translations": [True, False],
        "use_credential_store": [True, False],
        "with_libsecret": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_translations": False,
        "use_credential_store": False,
        "with_libsecret": False,
    }
    implements = ["auto_shared_fpic"]

    def config_options(self):
        if self.settings.os != "Windows":
            del self.options.fPIC
            del self.options.use_credential_store
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_libsecret

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _qt_options(self):
        options = {}
        if self.settings.os in ["Linux", "FreeBSD"]:
            options["with_dbus"] = True
        if self.options.build_translations:
            options["qttools"] = True
        if self.settings.os == "Android":
            options["qtandroidextras"] = True
        return options

    def requirements(self):
        self.requires("qt/[>=5 <7]", transitive_headers=True, transitive_libs=True, options=self._qt_options)
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.options.with_libsecret:
                self.requires("libsecret/[>=0.21.4 <1]")

    def validate(self):
        check_min_cppstd(self, 17 if self.settings.os == "Windows" else 11)
        qt_options = self.dependencies["qt"].options
        if self.settings.os in ["Linux", "FreeBSD"] and not qt_options.with_dbus:
            raise ConanInvalidConfiguration(f'{self.ref} requires -o qt/*:with_dbus=True on {self.settings.os}')

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.27 <5]")
        self.tool_requires("qt/<host_version>", options=self._qt_options)
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def validate_build(self):
        qt_options = self.dependencies["qt"].options
        if self.options.build_translations and not qt_options.qttools:
            raise ConanInvalidConfiguration(f"{self.ref} requires -o:b qt/*:qttools=True to build translations")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Allow Conan to set C++ standard
        replace_in_file(self,  "CMakeLists.txt",
                        "SET(CMAKE_CXX_STANDARD 11)", "")
        replace_in_file(self, os.path.join("qtkeychain", "CMakeLists.txt"),
                        "set(CMAKE_CXX_STANDARD 17)", "")
        # Fix linked targets
        replace_in_file(self, os.path.join("qtkeychain", "CMakeLists.txt"),
                        "${QTDBUS_LIBRARIES}", "Qt${QT_VERSION_MAJOR}::DBus")
        replace_in_file(self, os.path.join("qtkeychain", "CMakeLists.txt"),
                        "${QTANDROIDEXTRAS_LIBRARIES}", "Qt${QT_VERSION_MAJOR}::AndroidExtras")
        # Do not add build-time paths to RPATH
        replace_in_file(self, os.path.join("qtkeychain", "CMakeLists.txt"),
                        "INSTALL_RPATH_USE_LINK_PATH TRUE", "")
        # Fix a Qt6 incompatibility. Only the generated kwallet_interface.h header is used anyway.
        replace_in_file(self, os.path.join("qtkeychain", "CMakeLists.txt"),
                        "qt_add_dbus_interface(qtkeychain_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/org.kde.KWallet.xml kwallet_interface KWalletInterface)",
                        "qt_add_dbus_interface(qtkeychain_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/org.kde.KWallet.xml kwallet_interface)")

    def generate(self):
        # FIXME: workaround for libicui18n.so.75 not being found
        VirtualRunEnv(self).generate(scope="build")
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_WITH_QT6"] = self.dependencies["qt"].ref.version.major == 6
        tc.cache_variables["BUILD_TRANSLATIONS"] = self.options.build_translations
        tc.cache_variables["USE_CREDENTIAL_STORE"] = self.options.get_safe("use_credential_store", False)
        tc.cache_variables["LIBSECRET_SUPPORT"] = self.options.get_safe("with_libsecret", False)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        qt_major = self.dependencies["qt"].ref.version.major
        self.cpp_info.set_property("cmake_file_name", f"Qt{qt_major}Keychain")
        self.cpp_info.set_property("cmake_target_name", f"Qt{qt_major}Keychain::Qt{qt_major}Keychain")

        lib_postfix = "d" if self.settings.build_type == "Debug" and self.settings.os == "Windows" else ""
        self.cpp_info.libs = [f"qt{qt_major}keychain{lib_postfix}"]

        self.cpp_info.resdirs = ["mkspecs"]
        if self.options.build_translations:
            self.cpp_info.resdirs.append("share")

        self.cpp_info.requires = ["qt::qtCore"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.requires.extend(["qt::qtDBus"])
            if self.options.with_libsecret:
                self.cpp_info.requires.append("libsecret::libsecret")
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["crypt32"]
        elif is_apple_os(self):
            self.cpp_info.frameworks.extend(["Foundation", "Security"])
        elif self.settings.os == "Android":
            self.cpp_info.requires.append("qt::qtAndroidExtras")
