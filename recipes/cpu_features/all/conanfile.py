import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class CpuFeaturesConan(ConanFile):
    name = "cpu_features"
    license = "Apache-2.0"
    homepage = "https://github.com/google/cpu_features"
    description = "A cross platform C99 library to get cpu features at runtime."
    topics = ("cpu", "features", "cpuid")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if Version(self.version) < "0.7.0":
            tc.variables["BUILD_PIC"] = self.options.get_safe("fPIC", True)
        if Version(self.version) >= "0.7.0":
            tc.variables["BUILD_TESTING"] = False
        # TODO: should be handled by CMake helper
        if is_apple_os(self) and self.settings.arch in ["armv8", "armv8_32", "armv8.3"]:
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
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

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CpuFeatures")

        cpu_features = self.cpp_info.components["libcpu_features"]
        cpu_features.set_property("cmake_target_name", "CpuFeatures::cpu_features")
        cpu_features.libs = ["cpu_features"]
        cpu_features.includedirs = ["include/cpu_features"]
        if self.settings.os in ["Linux", "FreeBSD", "Android"]:
            cpu_features.system_libs = ["dl"]

        if self.settings.os == "Android":
            ndk_compat = self.cpp_info.components["ndk_compat"]
            ndk_compat.set_property("cmake_target_name", "CpuFeatures::ndk_compat")
            ndk_compat.libs = ["ndk_compat"]
            ndk_compat.includedirs = ["include/ndk_compat"]
            ndk_compat.system_libs = ["dl"]
