import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime

required_conan_version = ">=2.1"


class PackageConan(ConanFile):
    name = "smtpclient"
    description = "An SMTP client library built in C++ that support authentication and secure connections"
    license = "MIT"
    homepage = "https://github.com/jeremydumais/CPP-SMTPClient-library"
    topics = ("smtp", "email")
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
        self.requires("openssl/[<5]")

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "ssl crypto", "OpenSSL::Crypto OpenSSL::SSL")

    def generate(self):
        tc = CMakeToolchain(self)
        if is_msvc(self):
            tc.cache_variables["USE_MSVC_RUNTIME_LIBRARY_DLL"] = not is_msvc_static_runtime(self)
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = "OpenSSL::Crypto"
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = "OpenSSL::SSL"
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
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "smtpclient")
        self.cpp_info.set_property("cmake_target_name", "smtpclient::smtpclient")
        self.cpp_info.libdirs = [os.path.join("lib", "smtpclient")]
        self.cpp_info.libs = ["smtpclient"]
        if not self.options.shared:
            self.cpp_info.defines.append("SMTPCLIENT_STATIC")
