import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class TgbotConan(ConanFile):
    name = "tgbot"
    description = "C++ library for Telegram bot API"
    license = "MIT"
    homepage = "http://reo7sp.github.io/tgbot-cpp"
    topics = ("telegram", "telegram-api", "telegram-bot", "bot")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # tgbot/Api.h:#include <boost/property_tree/ptree.hpp>
        # Asio in v1.88 is not compatible
        self.requires("boost/[^1.71.0 <1.88]", transitive_headers=True, transitive_libs=True)
        # tgbot/net/CurlHttpClient.h:#include <curl/curl.h>
        self.requires("libcurl/[>=7.78 <9]", transitive_headers=True, transitive_libs=True)
        self.requires("openssl/[>=1.1 <4]")

    def validate(self):
        check_min_cppstd(self, "14" if Version(self.version) < "1.7.3" else "17")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Don't force PIC
        replace_in_file(self, "CMakeLists.txt", "set_property(TARGET ${PROJECT_NAME} PROPERTY POSITION_INDEPENDENT_CODE ON)", "")
        # Don't force CMAKE_CXX_STANDARD
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD", "#")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_TESTS"] = False
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        fix_apple_shared_install_name(self)
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["TgBot"]
        self.cpp_info.defines = ["HAVE_CURL=1"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
