import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class AafConan(ConanFile):
    name = "aaf"
    homepage = "https://sourceforge.net/projects/aaf/"
    description = (
        "A cross-platform SDK for AAF. AAF is a metadata management system and "
        "file format for use in professional multimedia creation and authoring."
    )
    topics = ("multimedia", "crossplatform")
    license = "AAFSDKPSL-2.0"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "structured_storage": [True, False],
    }
    default_options = {
        "structured_storage": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("expat/[>=2.6.2 <3]")
        self.requires("libjpeg/[>=9e]")
        if self.settings.os in ("FreeBSD", "Linux"):
            self.requires("util-linux-libuuid/[^2.41]")

    def validate(self):
        # Based on ref-impl/include/AAFPlatform.h
        supported = False
        supported |= is_apple_os(self) and self.settings.arch in ["armv8", "x86", "x86_64", "ppc32", "ppc64", "ppc64le"]
        supported |= self.settings.os == "Windows" and self.settings.arch in ["x86", "x86_64"]
        supported |= self.settings.os == "Linux" and self.settings.arch in ["x86", "x86_64", "ppc32", "ppc64", "ppc64le"]
        supported |= self.settings.os == "FreeBSD" and self.settings.arch in ["x86", "x86_64"]
        supported |= self.settings.os == "SunOS" and self.settings.arch in ["sparc"]
        if not supported:
            raise ConanInvalidConfiguration(f"{self.settings.os} {self.settings.arch} is not supported")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if is_apple_os(self):
            tc.cache_variables["PLATFORM"] = "apple-clang"
        elif is_msvc(self):
            tc.cache_variables["PLATFORM"] = "vc"
        else:
            tc.cache_variables["PLATFORM"] = str(self.settings.os)
        # ARCH is used only for setting the output directory, except if host is macOS
        # where ARCH is used to select proper pre-compiled proprietary Structured Storage library.
        if self.settings.os == "Macos" and self.settings.arch == "armv8":
            tc.cache_variables["ARCH"] = "arm64"
        else:
            tc.cache_variables["ARCH"] = "x86_64"
        tc.cache_variables["AAF_NO_STRUCTURED_STORAGE"] = not self.options.structured_storage
        jpeg_res_dirs = ";".join([p.replace("\\", "/") for p in self.dependencies["libjpeg"].cpp_info.aggregated_components().resdirs])
        tc.variables["JPEG_RES_DIRS"] = jpeg_res_dirs
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "AAFSDKPSL.TXT", src=os.path.join(self.source_folder, "LEGAL"), dst=os.path.join(self.package_folder, "licenses"))
        out_include_folder = os.path.join(self.source_folder, "out", "shared", "include")
        out_target_folder = os.path.join(self.source_folder, "out", "target")
        copy(self, "*.h", src=out_include_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "*/RefImpl/*.dll", src=out_target_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*/RefImpl/*.lib", src=out_target_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*/RefImpl/*.so*", src=out_target_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*/RefImpl/*.dylib", src=out_target_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*/RefImpl/*.a", src=out_target_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        fix_apple_shared_install_name(self)

    def package_info(self):
        if self.settings.os == "Windows":
            suffix = "D" if self.settings.build_type == "Debug" else ""
            self.cpp_info.libs = [f"AAF{suffix}", f"AAFIID{suffix}"]
            # The static library loads a DLL at runtime, on Windows it needs to be able
            # to find it in PATH, see https://aaf.sourceforge.net/AAFProjectFAQ.html
            self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        else:
            self.cpp_info.libs = ["aaflib", "aafiid"]
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["dl"]
        elif is_apple_os(self):
            self.cpp_info.frameworks = ["CoreServices", "CoreFoundation"]
