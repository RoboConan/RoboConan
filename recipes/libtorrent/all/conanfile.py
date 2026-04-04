import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibtorrentConan(ConanFile):
    name = "libtorrent"
    description = (
        "libtorrent is a feature complete C++ bittorrent implementation "
        "focusing on efficiency and scalability"
    )
    topics = ("p2p", "network", "mesh")
    homepage = "http://libtorrent.org"
    license = ("BSD-3-clause", "ZLIB", "BSL-1.0")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_deprecated_functions": [True, False],
        "enable_dht": [True, False],
        "enable_encryption": [True, False],
        "enable_exceptions": [True, False],
        "enable_extensions": [True, False],
        "enable_i2p": [True, False],
        "enable_iconv": [True, False],
        "enable_logging": [True, False],
        "enable_mutable_torrents": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_dht": True,
        "enable_deprecated_functions": True,
        "enable_encryption": True,
        "enable_exceptions": True,
        "enable_extensions": True,
        "enable_i2p": True,
        "enable_iconv": False,
        "enable_logging": True,
        "enable_mutable_torrents": True,
    }
    implements = ["auto_shared_fpic"]

    @property
    def _min_cppstd(self):
        return "11" if Version(self.version) < "2.0.0" else "14"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if Version(self.version) >= "2.0.0":
            self.requires("boost/[^1.71.0]", transitive_headers=True)
        else:
            self.requires("boost/[^1.71.0 <1.87]", transitive_headers=True)
        if self.options.enable_encryption:
            self.requires("openssl/[>=1.1 <4]", transitive_headers=True, transitive_libs=True)
        if self.options.enable_iconv:
            self.requires("libiconv/[^1.17]")

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)

    def build_requirements(self):
        if Version(self.version) >= "2.0.4":
            self.tool_requires("cmake/[>=3.16 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["Boost_USE_STATIC_LIBS"] = not self.dependencies["boost"].options.get_safe("shared", False)
        tc.variables["deprecated-functions"] = self.options.enable_deprecated_functions
        tc.variables["dht"] = self.options.enable_dht
        tc.variables["encryption"] = self.options.enable_encryption
        tc.variables["exceptions"] = self.options.enable_exceptions
        tc.variables["i2p"] = self.options.enable_i2p
        tc.variables["logging"] = self.options.enable_logging
        tc.variables["mutable-torrents"] = self.options.enable_mutable_torrents
        tc.variables["build_tests"] = False
        tc.variables["build_examples"] = False
        tc.variables["build_tools"] = False
        tc.variables["python-bindings"] = False
        tc.variables["python-bindings"] = False
        tc.variables["static_runtime"] = is_msvc_static_runtime(self)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"), "/W4", "")
        if Version(self.version) < "2.0":
            if self.options.enable_iconv:
                replace = "find_public_dependency(Iconv REQUIRED)"
            else:
                replace = "set(Iconv_FOUND OFF)"
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                                  "find_public_dependency(Iconv)",
                                  replace)

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "LibtorrentRasterbar")
        self.cpp_info.set_property("cmake_target_name", "LibtorrentRasterbar::torrent-rasterbar")
        self.cpp_info.set_property("pkg_config_name", "libtorrent-rasterbar")

        self.cpp_info.includedirs = ["include", os.path.join("include", "libtorrent")]
        self.cpp_info.libs = ["torrent-rasterbar"]

        self.cpp_info.requires = ["boost::headers"]
        if self.options.enable_encryption:
            self.cpp_info.requires.append("openssl::openssl")
        if self.options.enable_iconv:
            self.cpp_info.requires.append("libiconv::libiconv")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["dl", "pthread", "m"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["wsock32", "ws2_32", "iphlpapi", "dbghelp", "mswsock"]
        elif self.settings.os == "Macos":
            self.cpp_info.frameworks = ["CoreFoundation", "SystemConfiguration"]

        if self.options.shared:
            self.cpp_info.defines.append("TORRENT_LINKING_SHARED")
        if self.options.enable_encryption:
            self.cpp_info.defines.extend(["TORRENT_USE_OPENSSL", "TORRENT_USE_LIBCRYPTO"])
        else:
            self.cpp_info.defines.append("TORRENT_DISABLE_ENCRYPTION")
        if self.options.enable_iconv:
            self.cpp_info.defines.append("TORRENT_USE_ICONV")
        if not self.options.enable_dht:
            self.cpp_info.defines.append("TORRENT_DISABLE_DHT")
