import os

from conan import ConanFile
from conan.tools.build import check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class TinyExrConan(ConanFile):
    name = "tinyexr"
    description = "Tiny OpenEXR image loader/saver library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/syoyo/tinyexr"
    topics = ("exr", "image")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libdeflate": [True, False],
        "with_threads": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libdeflate": True,
        "with_threads": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    exports_sources = "CMakeLists.txt"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_libdeflate:
            self.requires("libdeflate/[^1.23]")

    def validate(self):
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TINYEXR_SRC_DIR"] = self.source_folder.replace("\\", "/")
        tc.variables["TINYEXR_VERSION"] = self.version
        tc.variables["TINYEXR_WITH_LIBDEFLATE"] = self.options.with_libdeflate
        tc.variables["TINYEXR_WITH_THREADS"] = self.options.with_threads
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="..")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tinyexr")
        self.cpp_info.set_property("cmake_target_name", "tinyexr::tinyexr")
        self.cpp_info.set_property("pkg_config_name", "tinyexr")
        self.cpp_info.libs = ["tinyexr3"]
        if self.options.with_libdeflate:
            self.cpp_info.requires.append("libdeflate::libdeflate")
        if self.options.with_threads and self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs.append("pthread")
