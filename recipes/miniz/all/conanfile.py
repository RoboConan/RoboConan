import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class MinizConan(ConanFile):
    name = "miniz"
    description = "Lossless, high performance data compression library that " \
                  "implements the zlib (RFC 1950) and Deflate (RFC 1951) " \
                  "compressed data format specification standards"
    license = "MIT"
    homepage = "https://github.com/richgel999/miniz"
    topics = ("zlib", "compression", "lossless")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "zlib_compat": [True, False],
        # For compatibility with libtorch
        "disable_crc32_checks": [True, False],
        "use_external_mzcrc": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "zlib_compat": False,
        "disable_crc32_checks": False,
        "use_external_mzcrc": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def config_options(self):
        if "pytorch" in self.version:
            self.options.disable_crc32_checks = True
            self.options.use_external_mzcrc = True

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.zlib_compat:
            self.provides = ["zlib"]

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        del self.info.options.zlib_compat

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_FUZZERS"] = False
        tc.variables["BUILD_TESTS"] = False
        tc.variables["AMALGAMATE_SOURCES"] = False
        tc.variables["BUILD_HEADER_ONLY"] = False
        tc.variables["INSTALL_PROJECT"] = True
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        if Version(self.version) <= "3.0.2":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        if self.options.disable_crc32_checks:
            tc.preprocessor_definitions["MINIZ_DISABLE_ZIP_READER_CRC32_CHECKS"] = "1"
        if self.options.use_external_mzcrc:
            tc.preprocessor_definitions["USE_EXTERNAL_MZCRC"] = "1"
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
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "miniz")
        self.cpp_info.set_property("cmake_target_name", "miniz::miniz")
        self.cpp_info.set_property("pkg_config_name", "miniz")
        self.cpp_info.libs = ["miniz"]
        self.cpp_info.includedirs.append(os.path.join("include", "miniz"))

        if self.options.zlib_compat:
            self.cpp_info.set_property("cmake_find_mode", "both")
            self.cpp_info.set_property("cmake_module_file_name", "ZLIB")
            self.cpp_info.set_property("cmake_module_target_name", "ZLIB::ZLIB")
            self.cpp_info.set_property("pkg_config_aliases", ["zlib"])
