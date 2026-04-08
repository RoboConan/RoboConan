import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class RoundingSatConan(ConanFile):
    name = "roundingsat"
    description = "RoundingSat solves decision and optimization problems formulated as 0-1 integer linear programs."
    license = "MIT"
    homepage = "https://gitlab.com/MIAOresearch/software/roundingsat"
    topics = ("optimization", "pseudo-boolean-solver", "sat", "linear-programming")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "prefixless_includes": [True, False],
        "with_soplex": [True, False],
        "with_gmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "prefixless_includes": False,
        "with_soplex": False,
        "with_gmp": False,
    }
    implements = ["auto_shared_fpic"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.shared
            del self.options.fPIC
            self.package_type = "static-library"

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        self.options["boost"].with_iostreams = True
        if self.settings.build_type == "Debug":
            self.options["boost"].stacktrace = True
            self.options["boost"].stacktrace_basic = True
            self.options["boost"].stacktrace_backtrace = True
            self.options["boost"].stacktrace_addr2line = True
            self.options["boost"].stacktrace_noop = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.71.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_soplex:
            self.requires("soplex/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.with_gmp:
            self.requires("gmp/[^6]")

    def validate(self):
        check_min_cppstd(self, 20 if Version(self.version) > "0.0+git.20240602" else 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Output a library instead of an executable
        replace_in_file(self, "src/roundingsat.cpp", "int main(", "int roundingsat_main(")
        replace_in_file(self, "CMakeLists.txt", "add_executable(", "add_library(")
        replace_in_file(self, "CMakeLists.txt",
                        "install(TARGETS roundingsat RUNTIME DESTINATION bin)",
                        "install(TARGETS roundingsat ARCHIVE DESTINATION lib LIBRARY DESTINATION lib RUNTIME DESTINATION bin)\n"
                        "install(DIRECTORY ${CMAKE_SOURCE_DIR}/src/ DESTINATION include/roundingsat FILES_MATCHING PATTERN *.hpp)")
        # Unvendor SoPlex
        save(self, "cmake/soplex_build_and_load.cmake", "find_package(soplex REQUIRED)\n")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["soplex"] = self.options.with_soplex
        tc.cache_variables["gmp"] = self.options.with_gmp
        if Version(self.version) > "0.0+git.20240602":
            commit = self.conan_data["sources"][self.version]["url"].split("/")[-2]
            tc.preprocessor_definitions["GIT_BRANCH"] = '"master"'
            tc.preprocessor_definitions["GIT_COMMIT_HASH"] = f'"{commit}"'
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("gmp", "cmake_file_name", "GMP")
        deps.set_property("soplex", "cmake_target_name", "libsoplex")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["roundingsat"]
        if self.options.prefixless_includes:
            self.cpp_info.includedirs.append("include/roundingsat")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "dl"]
        if self.options.with_soplex:
            self.cpp_info.defines.append("WITHSOPLEX")
        if self.options.with_gmp:
            self.cpp_info.defines.append("WITHGMP")
