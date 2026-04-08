import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd, valid_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import check_min_vs
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class Blend2dConan(ConanFile):
    name = "blend2d"
    description = "2D Vector Graphics Engine Powered by a JIT Compiler"
    license = "Zlib"
    homepage = "https://blend2d.com/"
    topics = ("2d-graphics", "rasterization", "asmjit", "jit")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_jit": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_jit": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_jit:
            self.requires("asmjit/[>=0.0+git.20240531]")

    def validate(self):
        check_min_cppstd(self, 11)

        if Version(self.version) < "0.8":
            # In Visual Studio < 16, there are compilation error. patch is already provided.
            # https://github.com/blend2d/blend2d/commit/63db360c7eb2c1c3ca9cd92a867dbb23dc95ca7d
            check_min_vs(self, 192)

    def build_requirements(self):
        if Version(self.version) >= "0.11.1":
            self.tool_requires("cmake/[>=3.18 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BLEND2D_TEST"] = False
        tc.variables["BLEND2D_EMBED"] = False
        tc.variables["BLEND2D_STATIC"] = not self.options.shared
        tc.variables["BLEND2D_NO_STDCXX"] = False
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.variables["BLEND2D_EXTERNAL_ASMJIT"] = True
        if not valid_min_cppstd(self, 11):
            tc.variables["CMAKE_CXX_STANDARD"] = 11
        if not self.options.shared:
            tc.preprocessor_definitions["BL_STATIC"] = "1"
        tc.variables["BLEND2D_NO_JIT"] = not self.options.with_jit
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "blend2d")
        self.cpp_info.set_property("cmake_target_name", "blend2d::blend2d")
        self.cpp_info.libs = ["blend2d"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["pthread", "rt",])
        if not self.options.shared:
            self.cpp_info.defines.append("BL_STATIC")
