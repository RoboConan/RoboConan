import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class CassandraCppDriverConan(ConanFile):
    name = "cassandra-cpp-driver"
    description = "DataStax C/C++ Driver for Apache Cassandra and DataStax Products"
    license = "Apache-2.0"
    homepage = "https://docs.datastax.com/en/developer/cpp-driver/"
    topics = ("cassandra", "cpp-driver", "database")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "install_header_in_subdir": [True, False],
        "use_atomic": [None, "boost", "std"],
        "with_openssl": [True, False],
        "with_zlib": [True, False],
        "with_kerberos": [True, False],
        "use_timerfd": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "install_header_in_subdir": False,
        "use_atomic": None,
        "with_openssl": True,
        "with_zlib": True,
        "with_kerberos": False,
        "use_timerfd": True,
    }

    @property
    def _min_cppstd(self):
        return 11

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.use_timerfd

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libuv/[^1.45.0]")
        self.requires("http_parser/2.9.4")
        self.requires("rapidjson/[>=0.0+git.20250205]")

        if self.options.with_openssl:
            self.requires("openssl/[>=1.1 <4]")

        if self.options.with_zlib:
            self.requires("minizip/[^1.2.13]")
            self.requires("zlib-ng/[^2.0]")

        if self.options.use_atomic == "boost":
            self.requires("boost/[^1.71.0]", libs=False)

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)

        if self.options.use_atomic == "boost":
            # Compilation error on Linux
            if self.settings.os == "Linux":
                raise ConanInvalidConfiguration(
                    "Boost.Atomic is not supported on Linux at the moment")

        if self.options.with_kerberos:
            raise ConanInvalidConfiguration(
                "Kerberos is not supported at the moment")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt",
                        '"${CMAKE_CXX_COMPILER_ID}" STREQUAL "Clang"',
                        '"${CMAKE_CXX_COMPILER_ID}" STREQUAL "Clang" OR "${CMAKE_CXX_COMPILER_ID}" STREQUAL "AppleClang"')
        rm(self, "Findlibssh2.cmake", "cmake")
        rm(self, "Findlibuv.cmake", "cmake")
        rm(self, "FindOpenSSL.cmake", "cmake")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["VERSION"] = self.version
        tc.variables["CASS_BUILD_EXAMPLES"] = False
        tc.variables["CASS_BUILD_INTEGRATION_TESTS"] = False
        tc.variables["CASS_BUILD_SHARED"] = self.options.shared
        tc.variables["CASS_BUILD_STATIC"] = not self.options.shared
        tc.variables["CASS_BUILD_TESTS"] = False
        tc.variables["CASS_BUILD_UNIT_TESTS"] = False
        tc.variables["CASS_DEBUG_CUSTOM_ALLOC"] = False
        tc.variables["CASS_INSTALL_HEADER_IN_SUBDIR"] = self.options.install_header_in_subdir
        tc.variables["CASS_INSTALL_PKG_CONFIG"] = False

        if self.options.use_atomic == "boost":
            tc.variables["CASS_USE_BOOST_ATOMIC"] = True
            tc.variables["CASS_USE_STD_ATOMIC"] = False

        elif self.options.use_atomic == "std":
            tc.variables["CASS_USE_BOOST_ATOMIC"] = False
            tc.variables["CASS_USE_STD_ATOMIC"] = True
        else:
            tc.variables["CASS_USE_BOOST_ATOMIC"] = False
            tc.variables["CASS_USE_STD_ATOMIC"] = False

        tc.variables["CASS_USE_OPENSSL"] = self.options.with_openssl
        tc.variables["CASS_USE_STATIC_LIBS"] = False
        tc.variables["CASS_USE_ZLIB"] = self.options.with_zlib
        tc.variables["CASS_USE_LIBSSH2"] = False

        # FIXME: To use kerberos, its conan package is needed. Uncomment this when kerberos conan package is ready.
        # tc.variables["CASS_USE_KERBEROS"] = self.options.with_kerberos

        if self.settings.os == "Linux":
            tc.variables["CASS_USE_TIMERFD"] = self.options.use_timerfd
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        if Version(self.version) > "2.17.1":
            raise ConanException("CMAKE_POLICY_VERSION_MINIMUM hardcoded to 3.5, check if new version supports CMake 4")
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["cassandra" if self.options.shared else "cassandra_static"]

        if self.settings.os == "Windows":
            self.cpp_info.system_libs.extend(["iphlpapi", "psapi", "wsock32",
                "crypt32", "ws2_32", "userenv", "version"])
            if not self.options.shared:
                self.cpp_info.defines = ["CASS_STATIC"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]

