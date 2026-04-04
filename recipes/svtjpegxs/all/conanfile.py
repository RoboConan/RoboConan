import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout, CMakeToolchain, CMake, CMakeDeps
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class SvtJpegXsConan(ConanFile):
    name = "svtjpegxs"
    description = "A JPEG XS (ISO/IEC 21122) compatible software encoder/decoder library"
    license = "BSD-2-Clause-Patent"
    homepage = "https://github.com/OpenVisualCloud/SVT-JPEG-XS"
    topics = ("jpegxs", "codec", "encoder", "decoder", "image", "video")
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

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cpuinfo/[*]")

    def build_requirements(self):
        self.tool_requires("nasm/[*]")

    def validate(self):
        if self.settings.arch not in ["x86", "x86_64"]:
            # INFO: The upstream only mentions support for x86, SSE and AVX
            # https://github.com/OpenVisualCloud/SVT-JPEG-XS/tree/v0.9.0?tab=readme-ov-file#environment-and-requirements
            raise ConanInvalidConfiguration(f"{self.ref} does not support {self.settings.arch}. Only x86 and x86_64 are supported.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        rmdir(self, "third_party/cpuinfo")
        save(self, "third_party/cpuinfo/CMakeLists.txt", "")
        replace_in_file(self, "CMakeLists.txt",
                        "set(CMAKE_POSITION_INDEPENDENT_CODE ON)",
                        "find_package(cpuinfo REQUIRED)\n"
                        "link_libraries(cpuinfo_public)\n")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_APPS"] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        tc.variables["ENABLE_NASM"] = True
        tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("cpuinfo", "cmake_target_name", "cpuinfo_public")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.configure()
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "SvtJpegxs")
        self.cpp_info.libs = ["SvtJpegxs"]
        self.cpp_info.includedirs.append("include/svt-jpegxs")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]

        if is_msvc(self) and self.options.shared:
            self.cpp_info.bindirs = ["lib"]
            self.cpp_info.defines.append("DEF_DLL")
