import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibFTPConan(ConanFile):
    name = "libftp"
    description = "A cross-platform FTP/FTPS client library based on Boost.Asio"
    license = "MIT"
    homepage = "https://github.com/deniskovalchuk/libftp"
    topics = ("ftp", "ftps", "boost", "ssl", "tls", "openssl")
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

    def configure(self):
        if Version(self.version) < "1.4.0" and is_msvc(self):
            del self.options.shared
            self.package_type = "static-library"
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.71.0 <1.88]", transitive_headers=True, libs=False)
        if Version(self.version) >= "0.5.0":
            self.requires("openssl/[<5]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LIBFTP_BUILD_TEST"] = False
        tc.variables["LIBFTP_BUILD_EXAMPLE"] = False
        tc.variables["LIBFTP_BUILD_CMDLINE_CLIENT"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["ftp"]

        self.cpp_info.set_property("cmake_file_name", "ftp")
        self.cpp_info.set_property("cmake_target_name", "ftp::ftp")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")

        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("ws2_32")
