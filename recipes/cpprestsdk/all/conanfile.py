import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class CppRestSDKConan(ConanFile):
    name = "cpprestsdk"
    description = "A project for cloud-based client-server communication in native code using a modern asynchronous " \
                  "C++ API design"
    homepage = "https://github.com/Microsoft/cpprestsdk"
    topics = ("rest", "client", "http", "https")
    license = "MIT"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_websockets": [True, False],
        "with_compression": [True, False],
        "pplx_impl": ["win", "winpplx"],
        "http_client_impl": ["winhttp", "asio"],
        "http_listener_impl": ["httpsys", "asio"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_websockets": True,
        "with_compression": True,
        "pplx_impl": "win",
        "http_client_impl": "winhttp",
        "http_listener_impl": "httpsys",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            del self.options.pplx_impl
            del self.options.http_client_impl
            del self.options.http_listener_impl

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _boost_modules(self):
        modules = []
        if self.settings.os != "Windows":
            modules += ["random", "thread", "filesystem", "chrono", "atomic"]
        elif self.settings.os != "Android":
            modules += ["date_time", "regex"]
        return modules

    def requirements(self):
        self.requires("boost/[^1.74.0 <1.87]", transitive_headers=True,
                      options={f"with_{module}": True for module in self._boost_modules})
        self.requires("openssl/[>=1.1 <4]")
        if self.options.with_compression:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_websockets:
            self.requires("websocketpp/0.8.2", options={"asio": "boost"})

    def validate(self):
        boost_opts = self.dependencies["boost"].options
        boost_missing = [mod for mod in self._boost_modules if not boost_opts.get_safe(f"with_{mod}")]
        if boost_missing:
            raise ConanInvalidConfiguration(f"Missing required Boost modules: {', '.join(boost_missing)}.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_SAMPLES"] = False
        tc.variables["WERROR"] = False
        tc.variables["CPPREST_EXCLUDE_WEBSOCKETS"] = not self.options.with_websockets
        tc.variables["CPPREST_EXCLUDE_COMPRESSION"] = not self.options.with_compression
        if self.options.get_safe("pplx_impl"):
            tc.variables["CPPREST_PPLX_IMPL"] = self.options.pplx_impl
        if self.options.get_safe("http_client_impl"):
            tc.variables["CPPREST_HTTP_CLIENT_IMPL"] = self.options.http_client_impl
        if self.options.get_safe("http_listener_impl"):
            tc.variables["CPPREST_HTTP_LISTENER_IMPL"] = self.options.http_listener_impl
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_clang_libcxx(self):
        if self.settings.compiler == 'clang' and str(self.settings.compiler.libcxx) in ['libstdc++', 'libstdc++11']:
            replace_in_file(self, os.path.join(self.source_folder, 'Release', 'CMakeLists.txt'),
                                  'libc++', 'libstdc++')

    def build(self):
        self._patch_clang_libcxx()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "license.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cpprestsdk"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cpprestsdk")

        # cpprestsdk_boost_internal
        self.cpp_info.components["cpprestsdk_boost_internal"].set_property("cmake_target_name", "cpprestsdk::cpprestsdk_boost_internal")
        self.cpp_info.components["cpprestsdk_boost_internal"].includedirs = []
        ## List of Boost components cpprestsdk depends on:
        ## see https://github.com/microsoft/cpprestsdk/blob/v2.10.19/Release/cmake/cpprest_find_boost.cmake#L77-L106
        self.cpp_info.components["cpprestsdk_boost_internal"].requires = [f"boost::{module}" for module in self._boost_modules]
        # cpprestsdk_openssl_internal
        self.cpp_info.components["cpprestsdk_openssl_internal"].set_property("cmake_target_name", "cpprestsdk::cpprestsdk_openssl_internal")
        self.cpp_info.components["cpprestsdk_openssl_internal"].includedirs = []
        self.cpp_info.components["cpprestsdk_openssl_internal"].requires = ["openssl::openssl"]
        # cpprest
        self.cpp_info.components["cpprest"].set_property("cmake_target_name", "cpprestsdk::cpprest")
        self.cpp_info.components["cpprest"].libs = collect_libs(self)
        self.cpp_info.components["cpprest"].requires = ["cpprestsdk_boost_internal", "cpprestsdk_openssl_internal"]
        if self.settings.os == "Linux":
            self.cpp_info.components["cpprest"].system_libs.append("pthread")
        elif self.settings.os == "Windows":
            if self.options.get_safe("http_client_impl") == "winhttp":
                self.cpp_info.components["cpprest"].system_libs.append("winhttp")
            if self.options.get_safe("http_listener_impl") == "httpsys":
                self.cpp_info.components["cpprest"].system_libs.append("httpapi")
            self.cpp_info.components["cpprest"].system_libs.append("bcrypt")
            if self.options.get_safe("pplx_impl") == "winpplx":
                self.cpp_info.components["cpprest"].defines.append("CPPREST_FORCE_PPLX=1")
            if self.options.get_safe("http_client_impl") == "asio":
                self.cpp_info.components["cpprest"].defines.append("CPPREST_FORCE_HTTP_CLIENT_ASIO")
            if self.options.get_safe("http_listener_impl") == "asio":
                self.cpp_info.components["cpprest"].defines.append("CPPREST_FORCE_HTTP_LISTENER_ASIO")
        elif self.settings.os == "Macos":
            self.cpp_info.components["cpprest"].frameworks.extend(["CoreFoundation", "Security"])
        if not self.options.shared:
            self.cpp_info.components["cpprest"].defines.extend(["_NO_ASYNCRTIMP", "_NO_PPLXIMP"])
        # cpprestsdk_zlib_internal
        if self.options.with_compression:
            self.cpp_info.components["cpprestsdk_zlib_internal"].set_property("cmake_target_name", "cpprestsdk::cpprestsdk_zlib_internal")
            self.cpp_info.components["cpprestsdk_zlib_internal"].includedirs = []
            self.cpp_info.components["cpprestsdk_zlib_internal"].requires = ["zlib-ng::zlib-ng"]
            self.cpp_info.components["cpprest"].requires.append("cpprestsdk_zlib_internal")
        # cpprestsdk_websocketpp_internal
        if self.options.with_websockets:
            self.cpp_info.components["cpprestsdk_websocketpp_internal"].set_property("cmake_target_name", "cpprestsdk::cpprestsdk_websocketpp_internal")
            self.cpp_info.components["cpprestsdk_websocketpp_internal"].includedirs = []
            self.cpp_info.components["cpprestsdk_websocketpp_internal"].requires = ["websocketpp::websocketpp"]
            self.cpp_info.components["cpprest"].requires.append("cpprestsdk_websocketpp_internal")
