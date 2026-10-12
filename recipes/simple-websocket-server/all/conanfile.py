import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class SimpleWebSocketServerConan(ConanFile):
    name = "simple-websocket-server"
    description = (
        "A very simple, fast, multithreaded, platform independent WebSocket (WS) "
        "and WebSocket Secure (WSS) server and client library."
    )
    license = "MIT"
    homepage = "https://gitlab.com/eidheim/Simple-WebSocket-Server"
    topics = ("websocket", "socket", "server", "client", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "use_asio_standalone": [True, False],
    }
    default_options = {
        "use_asio_standalone": True,
    }
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/[<5]")
        if self.options.use_asio_standalone:
            self.requires("asio/[^1.28.1]")
        else:
            self.requires("boost/[^1.71.0]", libs=False)

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", self.source_folder, os.path.join(self.package_folder, "include", "simple-websocket-server"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        if self.options.use_asio_standalone:
            self.cpp_info.defines.append("USE_STANDALONE_ASIO")
