import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class LlamaCppConan(ConanFile):
    name = "llama-cpp"
    description = "Inference of LLaMA model in pure C/C++"
    license = "MIT"
    homepage = "https://github.com/ggml-org/llama.cpp"
    topics = ("llama", "llm", "ai")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "server": [True, False],
        "with_cuda": [True, False],
        "with_curl": [True, False],
        "with_llguidance": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "server": False,
        "with_cuda": False,
        "with_curl": False,
        "with_llguidance": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_cuda:
            self.options["ggml"].with_cuda = True

    def package_id(self):
        del self.info.options.with_cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("ggml/[>=0.9.3 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("nlohmann_json/[^3]", transitive_headers=True)
        self.requires("minja/[^1]")
        if not self.options.with_curl or self.options.server:
            self.requires("cpp-httplib/[<1]")
        if self.options.with_curl:
            self.requires("libcurl/[>=7.78 <9]")
            self.requires("openssl/[<5]")
        if self.options.with_llguidance:
            self.requires("llguidance/[^1]")
        if self.options.tools:
            self.requires("stb/[*]")
            self.requires("miniaudio/[>=0.11 <1]")

    def validate_build(self):
        if self.settings.compiler == "msvc" and "arm" in self.settings.arch:
            raise ConanInvalidConfiguration("llama-cpp does not support ARM architecture on msvc, it recommends to use clang instead")

    def validate(self):
        if self.options.with_cuda and not self.dependencies["ggml"].options.with_cuda:
            raise ConanInvalidConfiguration("with_cuda=True requires -o ggml/*:with_cuda=True")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Unvendor
        rmdir(self, "vendor")
        replace_in_file(self, "tools/mtmd/mtmd-helper.cpp", "miniaudio/miniaudio.h", "miniaudio.h")
        replace_in_file(self, "tools/mtmd/mtmd-helper.cpp", "stb/stb_image.h", "stb_image.h")
        replace_in_file(self, "tools/server/utils.hpp", "cpp-httplib/httplib.h", "httplib.h")
        replace_in_file(self, "common/arg.cpp", "cpp-httplib/httplib.h", "httplib.h")
        # Fix `common` not being installed for a static build and give it a less clashing name.
        save(self, "common/CMakeLists.txt", textwrap.dedent("""\
            if(NOT BUILD_SHARED_LIBS)
                set_property(TARGET common PROPERTY OUTPUT_NAME llama_common)
                install(TARGETS common ARCHIVE DESTINATION lib LIBRARY DESTINATION lib RUNTIME DESTINATION bin)
            endif()
        """), append=True)
        # Add support for external llguidance
        replace_in_file(self, "common/CMakeLists.txt", "if (LLAMA_LLGUIDANCE)", textwrap.dedent("""\
            if (LLAMA_LLGUIDANCE)\n
                find_package(llguidance REQUIRED)\n
                target_compile_definitions(${TARGET} PUBLIC LLAMA_USE_LLGUIDANCE)\n
                list(APPEND LLAMA_COMMON_EXTRA_LIBS llguidance::llguidance)\n
            elseif(0)
        """))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_llama.cpp_INCLUDE"] = "conan_deps.cmake"
        tc.cache_variables["LLAMA_USE_SYSTEM_GGML"] = True
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["LLAMA_STANDALONE"] = False
        tc.cache_variables["LLAMA_BUILD_TESTS"] = False
        tc.cache_variables["LLAMA_BUILD_EXAMPLES"] = False
        tc.cache_variables["LLAMA_BUILD_TOOLS"] = self.options.tools
        tc.cache_variables["LLAMA_TOOLS_INSTALL"] = self.options.tools
        tc.cache_variables["LLAMA_BUILD_SERVER"] = self.options.server
        tc.cache_variables["LLAMA_CURL"] = self.options.with_curl
        tc.cache_variables["LLAMA_OPENSSL"] = self.options.with_curl
        tc.cache_variables["LLAMA_LLGUIDANCE"] = self.options.with_llguidance
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        copy(self, "*.h*", os.path.join(self.source_folder, "common"), os.path.join(self.package_folder, "include", "common"))
        copy(self, "*", os.path.join(self.source_folder, "models"), os.path.join(self.package_folder, "share", self.name, "models"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "llama")
        self.cpp_info.set_property("pkg_config_name", "llama")

        self.cpp_info.components["llama"].set_property("cmake_target_name", "llama")
        self.cpp_info.components["llama"].libs = ["llama"]
        self.cpp_info.components["llama"].resdirs = ["share"]
        self.cpp_info.components["llama"].requires = ["common"]

        if not self.options.shared:
            self.cpp_info.components["common"].libs = ["llama_common"]
        else:
            self.cpp_info.components["common"].libdirs = []
        self.cpp_info.components["common"].includedirs = ["include/common"]
        self.cpp_info.components["common"].requires = ["ggml::ggml", "nlohmann_json::nlohmann_json", "minja::minja"]
        if self.options.shared:
            self.cpp_info.components["llama"].defines.append("LLAMA_SHARED")
        if self.options.with_curl:
            self.cpp_info.components["common"].requires.extend(["libcurl::libcurl", "openssl::openssl"])
            self.cpp_info.components["common"].defines.append("LLAMA_USE_CURL")
        else:
            self.cpp_info.components["common"].requires.append("cpp-httplib::cpp-httplib")
        if self.options.with_llguidance:
            self.cpp_info.components["common"].requires.append("llguidance::llguidance")
            self.cpp_info.components["common"].defines.append("LLAMA_USE_LLGUIDANCE")
        if is_apple_os(self):
            self.cpp_info.components["common"].frameworks = ["Foundation", "Accelerate", "Metal"]
        elif self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["common"].system_libs = ["dl", "m", "pthread"]

        if self.options.tools:
            self.cpp_info.components["mtmd"].libs = ["mtmd"]
            self.cpp_info.components["mtmd"].requires = ["llama", "stb::stb", "miniaudio::miniaudio"]

        if self.options.server:
            self.cpp_info.components["_server"].requires = ["cpp-httplib::cpp-httplib"]
