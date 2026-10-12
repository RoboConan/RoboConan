import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class DateConan(ConanFile):
    name = "date"
    description = "A date and time library based on the C++11/14/17 <chrono> header"
    license = "MIT"
    homepage = "https://github.com/HowardHinnant/date"
    topics = ("datetime", "timezone", "calendar", "time", "iana-database")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "header_only": [True, False],
        "tzdb": ["download", "conan", "system", "manual"],
        "use_tz_db_in_dot": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "header_only": False,
        "tzdb": "system",
        "use_tz_db_in_dot": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            self.options["tz"].with_binary_db = False
        if self.settings.os in ["iOS", "tvOS", "watchOS", "Android"]:
            self.options.tzdb = "system"

    def configure(self):
        if self.options.shared or self.options.header_only:
            self.options.rm_safe("fPIC")
        if self.options.header_only:
            del self.options.shared
            self.package_type = "header-library"
            del self.options.tzdb

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("tzdb") == "conan":
            self.requires("tz/[*]")
        elif self.options.get_safe("tzdb") == "download":
            self.requires("libcurl/[>=7.78 <9]")

    def package_id(self):
        if self.info.options.header_only:
            self.info.clear()

    def validate(self):
        check_min_cppstd(self, 11)
        if self.options.get_safe("tzdb") != "download" and self.options.use_tz_db_in_dot:
            raise ConanInvalidConfiguration("'use_tz_db_in_dot=True' is only valid when 'tzdb=\"download\"'")
        if self.settings.os == "Windows":
            if self.options.get_safe("tzdb") == "system":
                # https://github.com/HowardHinnant/date/blob/v3.0.3/include/date/tz.h#L85-L89
                raise ConanInvalidConfiguration("'system' tzdb is not supported on Windows")
            if self.options.get_safe("tzdb") == "conan" and self.dependencies["tz"].options.with_binary_db:
                raise ConanInvalidConfiguration(
                    "date does not currently support parsing the binary tzdb on Windows. "
                    "An attempt has been made to introduce this in https://github.com/HowardHinnant/date/pull/611, "
                    "so if this is functionality you would like please feel free to adapt this to a conan patch."
                )

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.7 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_DATE_TESTING"] = False
        tc.variables["BUILD_TZ_LIB"] = True
        tc.variables["USE_TZ_DB_IN_DOT"] = self.options.use_tz_db_in_dot
        tc.variables["USE_SYSTEM_TZ_DB"] = self.options.get_safe("tzdb") in ["system", "conan"]
        tc.variables["MANUAL_TZ_DB"] = self.options.get_safe("tzdb") in ["manual", "conan"]
        # workaround for gcc 7 and clang 5 not having string_view
        if Version(self.version) >= "3.0.0" and \
                ((self.settings.compiler == "gcc" and Version(self.settings.compiler.version) <= "7.0") or
                 (self.settings.compiler == "clang" and Version(self.settings.compiler.version) <= "5.0")):
            tc.variables["DISABLE_STRING_VIEW"] = True
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        if not self.options.header_only:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        if not self.options.header_only:
            cmake = CMake(self)
            cmake.install()
            rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
            rmdir(self, os.path.join(self.package_folder, "CMake"))
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include", "date"),
                src=os.path.join(self.source_folder, "include", "date"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "date")
        self.cpp_info.set_property("cmake_target_name", "date::date")

        if self.options.header_only:
            self.cpp_info.bindirs = []
            self.cpp_info.libdirs = []
            self.cpp_info.defines.append("DATE_HEADER_ONLY")
        else:
            self.cpp_info.set_property("cmake_target_aliases", ["date::date-tz"])
            self.cpp_info.libs = ["date-tz" if Version(self.version) >= "3.0.0" else "tz"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs.extend(["m", "pthread"])
            if self.options.get_safe("tzdb") in ["system", "conan"]:
                self.cpp_info.defines.append("USE_OS_TZDB=1")
            if self.settings.os == "Windows" and self.options.shared:
                self.cpp_info.defines.append("DATE_USE_DLL=1")
