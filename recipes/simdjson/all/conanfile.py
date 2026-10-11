import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SimdjsonConan(ConanFile):
    name = "simdjson"
    description = "Parsing gigabytes of JSON per second"
    license = "Apache-2.0 OR MIT"
    homepage = "https://github.com/lemire/simdjson"
    topics = ("json", "parser", "simd", "format")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "threads": [True, False],
        "exceptions": [True, False],
        "disable_deprecated_api": [True, False],
        "static_reflection": [None, True, False],
        "minus_zero_as_float": [True, False],
        "enable_nan_inf": [True, False],
        "enable_memory_file_mapping": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "threads": True,
        "exceptions": True,
        "disable_deprecated_api": False,
        "static_reflection": None,
        "minus_zero_as_float": False,
        "enable_nan_inf": False,
        "enable_memory_file_mapping": False,
    }

    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def config_options(self):
        if Version(self.version) < "5":
            self.options.rm_safe("enable_nan_inf")
            self.options.rm_safe("enable_memory_file_mapping")
        elif self.settings.os != "Windows":
            self.options.rm_safe("enable_memory_file_mapping")

    @property
    def _static_reflection(self):
        option = self.options.get_safe("static_reflection")
        return None if option is None or str(option) == "None" else bool(option)

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SIMDJSON_ENABLE_THREADS"] = self.options.threads
        tc.variables["SIMDJSON_EXCEPTIONS"] = self.options.exceptions
        tc.variables["SIMDJSON_DISABLE_DEPRECATED_API"] = self.options.disable_deprecated_api
        tc.variables["SIMDJSON_MINUS_ZERO_AS_FLOAT"] = self.options.minus_zero_as_float
        tc.variables["SIMDJSON_DEVELOPER_MODE"] = False
        tc.variables["SIMDJSON_INSTALL"] = True
        tc.variables["SIMDJSON_SINGLEHEADER"] = True
        tc.variables["SIMDJSON_BUILD_STATIC_LIB"] = False

        static_reflection = self._static_reflection
        if static_reflection is not None:
            if Version(self.version) >= "5":
                tc.variables["SIMDJSON_STATIC_REFLECTION_MODE"] = "ON" if static_reflection else "OFF"
            else:
                tc.variables["SIMDJSON_STATIC_REFLECTION"] = static_reflection

        if self.options.get_safe("enable_nan_inf"):
            tc.variables["SIMDJSON_ENABLE_NAN_INF"] = True
        if self.options.get_safe("enable_memory_file_mapping"):
            tc.variables["SIMDJSON_ENABLE_MEMORY_FILE_MAPPING_ON_WINDOWS"] = True

        cppstd = self.settings.compiler.get_safe("cppstd")
        if cppstd:
            tc.variables["SIMDJSON_CXX_STANDARD"] = str(cppstd).replace("gnu", "")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "simdjson")
        self.cpp_info.set_property("cmake_target_name", "simdjson::simdjson")
        self.cpp_info.set_property("pkg_config_name", "simdjson")

        self.cpp_info.libs = ["simdjson"]
        if self.options.threads:
            self.cpp_info.defines.append("SIMDJSON_THREADS_ENABLED=1")
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs.append("pthread")
        if not self.options.exceptions:
            self.cpp_info.defines.append("SIMDJSON_EXCEPTIONS=0")
        if self.options.disable_deprecated_api:
            self.cpp_info.defines.append("SIMDJSON_DISABLE_DEPRECATED_API=1")
        if self._static_reflection is not None:
            if self._static_reflection:
                self.cpp_info.defines.append("SIMDJSON_STATIC_REFLECTION=1")
                if Version(self.version) < "5" or (
                    self.settings.compiler == "clang" and Version(self.settings.compiler.version) == "21"
                ):
                    self.cpp_info.cxxflags.extend([
                        "-freflection",
                        "-fexpansion-statements",
                        "-stdlib=libc++",
                        "-std=c++26",
                    ])
                else:
                    self.cpp_info.cxxflags.extend(["-freflection", "-std=c++26"])
            elif Version(self.version) >= "5":
                self.cpp_info.defines.append("SIMDJSON_STATIC_REFLECTION=0")
        if self.options.get_safe("enable_nan_inf"):
            self.cpp_info.defines.append("SIMDJSON_ENABLE_NAN_INF=1")
        if self.options.get_safe("enable_memory_file_mapping"):
            self.cpp_info.defines.extend([
                "SIMDJSON_ENABLE_MEMORY_FILE_MAPPING_ON_WINDOWS=1",
                "_WIN32_WINNT=0x0A00",
                "WINVER=0x0A00",
                "NTDDI_VERSION=0x0A000006",
            ])
            self.cpp_info.system_libs.append("onecore")
        if self.options.shared and is_msvc(self):
            self.cpp_info.defines.append("SIMDJSON_USING_WINDOWS_DYNAMIC_LIBRARY=1")
