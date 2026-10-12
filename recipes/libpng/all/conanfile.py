import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class LibpngConan(ConanFile):
    name = "libpng"
    description = "libpng is the official PNG file format reference library."
    homepage = "http://www.libpng.org"
    license = "libpng-2.0"
    topics = ("png", "graphics", "image")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "neon": [True, "check", False],
        "msa": [True, False],
        "sse": [True, False],
        "vsx": [True, False],
        "api_prefix": ["ANY"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "neon": True,
        "msa": True,
        "sse": True,
        "vsx": True,
        "api_prefix": "",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    @property
    def _is_clang_cl(self):
        return self.settings.os == "Windows" and self.settings.compiler == "clang" and \
               self.settings.compiler.get_safe("runtime")

    @property
    def _has_neon_support(self):
        return "arm" in self.settings.arch

    @property
    def _has_msa_support(self):
        return "mips" in self.settings.arch

    @property
    def _has_sse_support(self):
        return self.settings.arch in ["x86", "x86_64"]

    @property
    def _has_vsx_support(self):
        return "ppc" in self.settings.arch

    @property
    def _neon_msa_sse_vsx_mapping(self):
        return {
            "True": "on",
            "False": "off",
            "check": "check",
        }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not self._has_neon_support:
            del self.options.neon
        if not self._has_msa_support:
            del self.options.msa
        if not self._has_sse_support:
            del self.options.sse
        if not self._has_vsx_support:
            del self.options.vsx

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["PNG_TESTS"] = False
        tc.cache_variables["PNG_SHARED"] = self.options.shared
        tc.cache_variables["PNG_STATIC"] = not self.options.shared
        tc.cache_variables["PNG_DEBUG"] = self.settings.build_type == "Debug"
        tc.cache_variables["PNG_PREFIX"] = self.options.api_prefix
        if self._has_neon_support:
            tc.cache_variables["PNG_ARM_NEON"] = self._neon_msa_sse_vsx_mapping[str(self.options.neon)]
        if self._has_msa_support:
            tc.cache_variables["PNG_MIPS_MSA"] = self._neon_msa_sse_vsx_mapping[str(self.options.msa)]
        if self._has_sse_support:
            tc.cache_variables["PNG_INTEL_SSE"] = self._neon_msa_sse_vsx_mapping[str(self.options.sse)]
        if self._has_vsx_support:
            tc.cache_variables["PNG_POWERPC_VSX"] = self._neon_msa_sse_vsx_mapping[str(self.options.vsx)]
        tc.cache_variables["PNG_FRAMEWORK"] = False  # changed from False to True by default in PNG 1.6.41
        tc.cache_variables["PNG_TOOLS"] = False
        tc.cache_variables["CMAKE_MACOSX_BUNDLE"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Remove libpng-config scripts
        if self.options.shared:
            rm(self, "*[!.dll]", os.path.join(self.package_folder, "bin"))
        else:
            rmdir(self, os.path.join(self.package_folder, "bin"))
        # .pc files
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # CMake config files
        rmdir(self, os.path.join(self.package_folder, "lib", "libpng"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # man pages
        rmdir(self, os.path.join(self.package_folder, "share"))
        # Remove duplicated headers under include/ and include/libpng<version>
        rm(self, "*.h", os.path.join(self.package_folder, "include"), recursive=False)

    def package_info(self):
        major_min_version = f"{Version(self.version).major}{Version(self.version).minor}"

        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "PNG")
        self.cpp_info.set_property("cmake_target_name", "PNG::PNG")
        self.cpp_info.set_property("cmake_target_aliases", ["PNG::png_shared" if self.options.shared else "PNG::png_static"])
        self.cpp_info.set_property("pkg_config_name", "libpng")
        self.cpp_info.set_property("pkg_config_aliases", [f"libpng{major_min_version}"])

        self.cpp_info.includedirs.append(f"include/libpng{major_min_version}")

        prefix = "lib" if (is_msvc(self) or self._is_clang_cl) else ""
        suffix = major_min_version
        if self.settings.os == "Windows":
            if not self.options.shared:
                suffix += "_static"
            if self.settings.build_type == "Debug":
                suffix += "d"
        self.cpp_info.libs = [f"{prefix}png{suffix}"]
        if self.settings.os in ["Linux", "Android", "FreeBSD", "SunOS", "AIX"]:
            self.cpp_info.system_libs.append("m")
