import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class BZip3Conan(ConanFile):
    name = "bzip3"
    description = "A better and stronger spiritual successor to BZip2."
    license = "LGPL-3.0"
    homepage = "https://github.com/iczelia/bzip3"
    topics = ("bzip2", "lzma", "compression")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_thread": [True, False],
        "with_util": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_thread": True,
        "with_util": False,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        # FIXME: could be supported on Windows:
        #  - MinGW with posix thread supports it out of the box
        #  - otherwise, add pthreads4w to requirements and link it in CMakeLists
        if self.settings.os == "Windows":
            del self.options.with_thread

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if Version(self.version) >= "1.5.4":
            tc.variables["BZIP3_ENABLE_PTHREAD"] = self.options.get_safe("with_thread", False)
            tc.variables["BZIP3_BUILD_APPS"] = self.options.with_util
            tc.variables["BZIP3_ENABLE_STATIC_EXE"] = False
            tc.variables["CMAKE_SKIP_RPATH"] = True
        else:
            tc.variables["BZIP3_SRC_DIR"] = self.source_folder.replace("\\", "/")
            tc.variables["BZIP3_WITH_PTHREAD"] = self.options.get_safe("with_thread", False)
            tc.variables["BZIP3_WITH_UTIL"] = self.options.with_util
            tc.variables["BZIP3_VERSION"] = self.version
        tc.generate()

    def build(self):
        cmake = CMake(self)
        if Version(self.version) >= "1.5.4":
            cmake.configure()
        else:
            cmake.configure(build_script_folder="..")
        cmake.build()

    def package(self):
        copy(self, "*LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        if Version(self.version) >= "1.5.4":
            self.cpp_info.set_property("cmake_file_name", "bzip3")
            self.cpp_info.set_property("cmake_target_name", "bzip3::bz3")
        self.cpp_info.set_property("pkg_config_name", "bzip3")
        self.cpp_info.libs = ["bzip3"]
        if self.settings.os == "Windows" and self.options.shared and Version(self.version) >= "1.5.4":
            self.cpp_info.defines.append("BZIP3_DLL_IMPORT=1")
        if self.settings.os in ["Linux", "FreeBSD"]:
            if Version(self.version) < "1.5.4":
                self.cpp_info.system_libs.append("m")
            if self.options.get_safe("with_thread", False):
                self.cpp_info.system_libs.append("pthread")
