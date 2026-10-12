import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class QuickfixConan(ConanFile):
    name = "quickfix"
    description = "QuickFIX is a free and open source implementation of the FIX protocol"
    license = "DocumentRef-LICENSE:LicenseRef-QuickFIX-Software-License-1.0"
    homepage = "http://www.quickfixengine.org"
    topics = ("FIX", "Financial Information Exchange", "libraries", "cpp")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
        "with_postgres": [True, False],
        "with_mysql": [None, "libmysqlclient"],
        "enable_boost_atomic_count": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": False,
        "with_postgres": False,
        "with_mysql": None,
        "enable_boost_atomic_count": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not is_msvc(self) and self.settings.arch not in ["x86", "x86_64"]:
            # Otherwise inline x86 assembly is used for atomic operations.
            self.options.enable_boost_atomic_count = True

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_ssl:
            self.requires("openssl/[<5]")
        if self.options.with_postgres:
            self.requires("libpq/[^17.0]")
        if self.options.with_mysql == "libmysqlclient":
            self.requires("libmysqlclient/[^8.1.0]")
        if self.options.enable_boost_atomic_count:
            self.requires("boost/[^1.71.0]", libs=False)

    def validate(self):
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration("QuickFIX cannot be built as shared lib on Windows")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["HAVE_SSL"] = self.options.with_ssl
        tc.variables["HAVE_POSTGRESQL"] = self.options.with_postgres
        tc.variables["HAVE_MYSQL"] = bool(self.options.with_mysql)
        if self.options.enable_boost_atomic_count:
            tc.preprocessor_definitions["ENABLE_BOOST_ATOMIC_COUNT"] = None
            inc = self.dependencies["boost"].cpp_info.includedir
            tc.extra_cxxflags.append(f"-I{inc}")
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="quickfix")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "config.h",
             dst=os.path.join(self.package_folder, "include", "quickfix"),
             src=self.build_folder)
        copy(self, "Except.h",
            dst=os.path.join(self.package_folder, "include"),
            src=os.path.join(self.source_folder, "src", "C++"))
        copy(self, "LICENSE",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)

        if self.options.with_ssl:
            self.cpp_info.defines.append("HAVE_SSL=1")

        if self.options.with_postgres:
            self.cpp_info.defines.append("HAVE_POSTGRESQL=1")

        if self.options.with_mysql:
            self.cpp_info.defines.append("HAVE_MYSQL=1")

        if self.settings.os == "Windows":
            self.cpp_info.system_libs.extend(["ws2_32"])
        elif self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["pthread", "m"])

        if self.options.with_ssl:
            self.cpp_info.requires.append("openssl::openssl")
        if self.options.with_postgres:
            self.cpp_info.requires.append("libpq::libpq")
        if self.options.with_mysql == "libmysqlclient":
            self.cpp_info.requires.append("libmysqlclient::libmysqlclient")
        if self.options.enable_boost_atomic_count:
            self.cpp_info.requires.append("boost::headers")
