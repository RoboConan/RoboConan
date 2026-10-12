import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class WebsocketPPConan(ConanFile):
    name = "websocketpp"
    description = "Header only C++ library that implements RFC6455 The WebSocket Protocol"
    topics = ("websocketpp", "websocket", "network", "web", "rfc6455", "header-only")
    homepage = "https://github.com/zaphoyd/websocketpp"
    license = "BSD-3-Clause"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "asio": ["boost", "standalone", False],
        "with_openssl": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "asio": "standalone",
        "with_openssl": True,
        "with_zlib": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.options["boost"].with_random = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_openssl:
            self.requires("openssl/[<5]", transitive_headers=True, transitive_libs=True)

        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]", transitive_headers=True, transitive_libs=True)

        if self.options.asio == "standalone":
            self.requires("asio/[>=1.28.1 <1.32]", transitive_headers=True)
        elif self.options.asio == "boost":
            self.requires("boost/[^1.71.0 <1.88]", transitive_headers=True)

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, os.path.join("websocketpp","*.hpp"), self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "websocketpp")
        self.cpp_info.set_property("cmake_target_name", "websocketpp::websocketpp")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.requires = []
        if self.options.with_openssl:
            self.cpp_info.requires.append("openssl::openssl")
        if self.options.with_zlib:
            self.cpp_info.requires.append("zlib-ng::zlib-ng")
        if self.options.asio == "standalone":
            self.cpp_info.defines.extend(["ASIO_STANDALONE", "_WEBSOCKETPP_CPP11_STL_"])
            self.cpp_info.requires.append("asio::asio")
        elif self.options.asio == "boost":
            self.cpp_info.requires.extend(["boost::headers", "boost::random"] )
