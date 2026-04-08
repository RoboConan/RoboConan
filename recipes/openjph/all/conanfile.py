import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OpenJPH(ConanFile):
    name = "openjph"
    description = "Open-source implementation of JPEG2000 Part-15 (or JPH or HTJ2K)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/aous72/OpenJPH"
    topics = ("ht-j2k", "jpeg2000", "jp2", "openjph", "image", "multimedia", "format", "graphics")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_executables": [True, False],
        "with_tiff": [True, False],
        "with_stream_expand_tool": [True, False],
        "disable_simd": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_executables": False,
        "with_tiff": True,
        "with_stream_expand_tool": False,
        "disable_simd": False,
    }
    implements = ["auto_shared_fpic"]

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_executables:
            del self.options.with_tiff

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("with_tiff"):
            self.requires("libtiff/[>=4.5 <5]")

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "src/core/CMakeLists.txt",
                        "set_target_properties(openjph PROPERTIES POSITION_INDEPENDENT_CODE ON)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["OJPH_BUILD_EXECUTABLES"] = self.options.with_executables
        tc.cache_variables["OJPH_ENABLE_TIFF_SUPPORT"] = self.options.get_safe("with_tiff", False)
        tc.cache_variables["OJPH_BUILD_STREAM_EXPAND"] = self.options.with_stream_expand_tool
        tc.cache_variables["OJPH_DISABLE_SIMD"] = self.options.disable_simd
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake .configure()
        cmake .build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "openjph")
        self.cpp_info.set_property("cmake_target_name", "openjph::openjph")
        self.cpp_info.set_property("pkg_config_name", "openjph")

        version_suffix = "_d" if self.settings.build_type == "Debug" else ""
        if is_msvc(self):
            v = Version(self.version)
            version_suffix = f".{v.major}.{v.minor}"
            if self.settings.build_type == "Debug":
                version_suffix += "d"
        self.cpp_info.libs = ["openjph" + version_suffix]
