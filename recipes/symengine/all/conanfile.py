import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SymengineConan(ConanFile):
    name = "symengine"
    description = "A fast symbolic manipulation library, written in C++"
    license = "MIT"
    topics = ("symbolic", "algebra")
    homepage = "https://symengine.org/"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "integer_class": ["boostmp", "gmp"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "integer_class": "gmp",
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "7":
            raise ConanInvalidConfiguration(f"{self.ref} requires GCC >= 7")

    @property
    def _needs_fast_float(self):
        return Version(self.version) >= "0.13.0"

    def requirements(self):
        if self.options.integer_class == "boostmp":
            # symengine/mp_class.h:12
            self.requires("boost/[^1.71.0]", transitive_headers=True, libs=False)
        else:
            self.requires("gmp/[^6.3.0]", transitive_headers=True, transitive_libs=True)
        if self._needs_fast_float:
            self.requires("fast_float/[^6.1.5]")

    def source(self):
        if "symforce" not in self.version:
            get(self, **self.conan_data["sources"][self.version], strip_root=True)
        else:
            get(self, **self.conan_data["sources"][self.version], strip_root=True,
                pattern="*/third_party/symengine/*", destination="..")
            move_folder_contents(self, "../third_party/symengine", self.source_folder)
        apply_conandata_patches(self)
        # Disable hardcoded C++11
        replace_in_file(self, "CMakeLists.txt",
                        'set(CMAKE_CXX_FLAGS "${CXX11_OPTIONS} ${CMAKE_CXX_FLAGS}")',
                        '')
        # Let Conan choose fPIC
        replace_in_file(self, "CMakeLists.txt",
                        'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${common}")',
                        '')
        # cmake_target_name not working?
        replace_in_file(self, "CMakeLists.txt",
                        "set(LIBS ${LIBS} ${GMP_TARGETS})",
                        "set(LIBS ${LIBS} gmp::gmp)")
        if Version(self.version) < "0.9":
            replace_in_file(self, "cmake/cotire.cmake",
                            "cmake_minimum_required(VERSION 2.8.12)",
                            "cmake_minimum_required(VERSION 3.10)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["BUILD_BENCHMARKS"] = False
        tc.cache_variables["INTEGER_CLASS"] = self.options.integer_class
        tc.cache_variables["MSVC_USE_MT"] = is_msvc_static_runtime(self)
        if self._needs_fast_float:
            tc.cache_variables["WITH_SYSTEM_FASTFLOAT"] = True
        if Version(self.version) < "0.14":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("gmp", "cmake_file_name", "GMP")
        # If we ever add support for gmpxx, we should set this property
        # deps.set_property("gmp::gmpxx", "cmake_target_name", "gmpxx")
        deps.set_property("fast_float", "cmake_file_name", "FASTFLOAT")
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
        rmdir(self, os.path.join(self.package_folder, "CMake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SymEngine")
        self.cpp_info.set_property("cmake_target_name", "symengine")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["SYMENGINE"])
        self.cpp_info.libs = ["symengine"]
        if "teuchos" in collect_libs(self):
            self.cpp_info.libs.append("teuchos")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
