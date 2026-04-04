import os
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class XZUtilsConan(ConanFile):
    name = "xz_utils"
    description = (
        "XZ Utils is free general-purpose data compression software with a high "
        "compression ratio. XZ Utils were written for POSIX-like systems, but also "
        "work on some not-so-POSIX systems. XZ Utils are the successor to LZMA Utils."
    )
    license = "0BSD"
    homepage = "https://tukaani.org/xz"
    topics = ("lzma", "xz", "compression")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "tools": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        rmdir(self, "tests")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["XZ_NLS"] = self.options.i18n
        tc.cache_variables["XZ_TOOL_LZMADEC"] = self.options.tools
        tc.cache_variables["XZ_TOOL_LZMAINFO"] = self.options.tools
        tc.cache_variables["XZ_TOOL_LZMAINFO"] = self.options.tools
        tc.cache_variables["XZ_TOOL_SCRIPTS"] = self.options.tools
        tc.cache_variables["XZ_TOOL_XZ"] = self.options.tools
        tc.cache_variables["XZ_TOOL_XZDEC"] = self.options.tools
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.0BSD", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        self._create_cmake_module_variables(os.path.join(self.package_folder, self._module_file_rel_path))

    def _create_cmake_module_variables(self, module_file):
        content = textwrap.dedent(f"""\
            set(LIBLZMA_FOUND TRUE)
            set(LIBLZMA_VERSION_MAJOR {Version(self.version).major})
            set(LIBLZMA_VERSION_MINOR {Version(self.version).minor})
            set(LIBLZMA_VERSION_PATCH {Version(self.version).patch})
            set(LIBLZMA_VERSION_STRING "{self.version}")
            set(LIBLZMA_HAS_AUTO_DECODER TRUE)
            set(LIBLZMA_HAS_EASY_ENCODER TRUE)
            set(LIBLZMA_HAS_LZMA_PRESET TRUE)
        """)
        save(self, module_file, content)

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-variables.cmake")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "LibLZMA")
        self.cpp_info.set_property("cmake_target_name", "LibLZMA::LibLZMA")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["LIBLZMA"])
        self.cpp_info.set_property("cmake_build_modules", [self._module_file_rel_path])
        self.cpp_info.set_property("pkg_config_name", "liblzma")
        self.cpp_info.libs = ["lzma"]
        if self.options.i18n:
            self.cpp_info.resdirs = ["share"]
        if not self.options.shared:
            self.cpp_info.defines.append("LZMA_API_STATIC")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread"]
