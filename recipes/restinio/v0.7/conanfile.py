import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class RestinioConan(ConanFile):
    name = "restinio"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Stiffstream/restinio"
    description = "RESTinio is a header-only C++17 library that gives you an embedded HTTP/Websocket server."
    topics = ("http-server", "websockets", "rest", "tls-support")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "asio": ["boost", "standalone"],
        "with_openssl": [True, False],
        "with_zlib": [True, False],
        "with_pcre": [1, 2, None],
    }
    default_options = {
        "asio": "standalone",
        "with_openssl": False,
        "with_zlib": False,
        "with_pcre": None,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("llhttp/[^9.1.3]")
        self.requires("fmt/[^5]")
        self.requires("expected-lite/[>=0.6.3 <1]")

        if self.options.asio == "standalone":
            self.requires("asio/[^1.28.0]")
        else:
            self.requires("boost/[^1.71.0 <1.88]", libs=False)

        if self.options.with_openssl:
            self.requires("openssl/[<5]")

        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")

        if self.options.with_pcre == 1:
            self.requires("pcre/[^8.45]")
        elif self.options.with_pcre == 2:
            self.requires("pcre2/[^10.42]")

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.*pp", src=os.path.join(self.source_folder, "dev", "restinio"), dst=os.path.join(self.package_folder, "include", "restinio"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "restinio")
        self.cpp_info.set_property("cmake_target_name", "restinio::restinio")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.options.asio == "boost":
            self.cpp_info.defines.append("RESTINIO_USE_BOOST_ASIO")
