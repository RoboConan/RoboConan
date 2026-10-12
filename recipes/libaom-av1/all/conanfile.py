import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibaomAv1Conan(ConanFile):
    name = "libaom-av1"
    description = "AV1 Codec Library"
    topics = ("av1", "codec", "video", "encoding", "decoding")
    homepage = "https://aomedia.googlesource.com/aom"
    license = "BSD-2-Clause"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "assembly": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "assembly": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch not in ("x86", "x86_64"):
            del self.options.assembly

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")
        if self.options.get_safe("assembly", False):
            self.tool_requires("nasm/[*]")
        if self.settings_build.os == "Windows":
            self.tool_requires("strawberryperl/[^5.32.1.1]")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_EXAMPLES"] = False
        tc.variables["ENABLE_TESTS"] = False
        tc.variables["ENABLE_DOCS"] = False
        tc.variables["ENABLE_TOOLS"] = False
        tc.variables["ENABLE_APPS"] = False
        if not self.options.get_safe("assembly", False):
            # make non-assembly build
            tc.variables["AOM_TARGET_CPU"] = "generic"
        # libyuv is used for examples, tests and non-essential 'dump_obu' tool so it is disabled
        # required to be 1/0 instead of False
        tc.variables["CONFIG_LIBYUV"] = 0
        # webm is not yet packaged
        tc.variables["CONFIG_WEBM_IO"] = 0
        if self.settings.get_safe("compiler.cstd"):
            tc.variables["CMAKE_C_STANDARD"] = str(self.settings.compiler.cstd)
        else:
            tc.variables["CMAKE_C_STANDARD"] = "11" if Version(self.version) >= "3.15.0" else "99"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "aom")
        lib = "aom"
        if self.settings.os == "Windows" and self.options.shared:
            lib = "aom_dll"
        self.cpp_info.libs = [lib]
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["pthread", "m"]
