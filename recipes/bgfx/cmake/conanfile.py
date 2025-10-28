import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class bgfxConan(ConanFile):
    name = "bgfx"
    license = "BSD-2-Clause"
    homepage = "https://github.com/bkaradzic/bgfx"
    description = "Cross-platform rendering library"
    topics = ("rendering", "graphics", "gamedev")
    package_type = "library"
    settings = "os", "compiler", "arch", "build_type"
    options = {
        "fPIC": [True, False],
        "shared": [True, False],
        "tools": [True, False],
    }
    default_options = {
        "fPIC": True,
        "shared": False,
        "tools": False,
    }
    # INFO: bgfx supports shared, but only generates bgfx as shared and all others as static
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.settings.os == "Linux":
            # INFO: X11 and OpenGL are mandatory - bgfx.cmake:184
            self.requires("xorg/system")
            self.requires("opengl/system")
            # INFO: Wayland is optional, but we enable it by default on Linux - CMakeLists.txt:46
            self.requires("wayland/[^1.23.92]")
        # INFO: miniz, tinyexr and libsquish are vendored in bgfx as well
        self.requires("miniz/[^3.0.2]")
        if not self.options.shared:
            # INFO: bimg_encode and bimg_decode are only built for static bgfx
            self.requires("tinyexr/[^1.0.7]")
            self.requires("libsquish/[^1.15]")
            self.requires("lodepng/[*]")
        # INFO: glflags and spirv-tools are vendored only. No need to add them as dependencies

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "bimg/src/image_decode.cpp", "miniz.c", "miniz.h")

    def generate(self):
        tc = CMakeToolchain(self)
        # bgfx does not include dependencies via find_package
        tc.cache_variables["CMAKE_PROJECT_bgfx_INCLUDE"] = "conan_deps.cmake"
        # It supports shared, but only generates bgfx as shared and all others as static
        tc.cache_variables["BGFX_LIBRARY_TYPE"] = "SHARED" if self.options.shared else "STATIC"
        tc.cache_variables["BGFX_BUILD_EXAMPLES"] = False
        tc.cache_variables["BGFX_BUILD_EXAMPLE_COMMON"] = False
        tc.cache_variables["BGFX_BUILD_TESTS"] = False
        tc.cache_variables["BGFX_INSTALL"] = True
        tc.cache_variables["BGFX_BUILD_TOOLS"] = self.options.tools
        tc.cache_variables["BX_AMALGAMATED"] = True
        tc.cache_variables["BGFX_AMALGAMATED"] = True
        tc.cache_variables["BGFX_OPENGLES_VERSION"] = 30
        tc.generate()
        deps = CMakeDeps(self)
        if self.settings.os == "Linux":
            deps.set_property("miniz", "cmake_additional_variables_prefixes", ["MINIZ",])
            deps.set_property("tinyexr", "cmake_additional_variables_prefixes", ["TINYEXR",])
            deps.set_property("libsquish", "cmake_additional_variables_prefixes", ["LIBSQUISH",])
            deps.set_property("wayland", "cmake_target_name", "wayland-egl")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "bgfxTargets*", os.path.join(self.package_folder, "lib", "cmake", "bgfx"))
        rm(self, "bgfxConfig*", os.path.join(self.package_folder, "lib", "cmake", "bgfx"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "bgfx")
        self.cpp_info.set_property("cmake_build_modules", ["lib/cmake/bgfx/bgfxToolUtils.cmake"])

        self.cpp_info.components["bx"].set_property("cmake_target_name", "bgfx::bx")
        self.cpp_info.components["bx"].libs = ["bx"]
        self.cpp_info.components["bx"].defines = [f"BX_CONFIG_DEBUG={1 if self.settings.build_type == 'Debug' else 0}"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["bx"].system_libs = ["dl", "rt"]
            self.cpp_info.components["bx"].includedirs.append("include/bx/compat/linux")
        elif is_apple_os(self):
            self.cpp_info.components["bx"].frameworks = ["Foundation"]
            self.cpp_info.components["bx"].includedirs.append("include/bx/compat/osx")
        elif is_msvc(self):
            # INFO: \bx\platform.h(432): fatal error C1189: #error:  "When using MSVC you must set /Zc:__cplusplus compiler option."
            self.cpp_info.components["bx"].cxxflags = ["/Zc:__cplusplus", "/Zc:preprocessor"]
            self.cpp_info.components["bx"].includedirs.append("include/bx/compat/msvc")
            self.cpp_info.components["bx"].defines.extend(["__STDC_LIMIT_MACROS", "__STDC_FORMAT_MACROS", "__STDC_CONSTANT_MACROS"])

        self.cpp_info.components["bimg"].set_property("cmake_target_name", "bgfx::bimg")
        self.cpp_info.components["bimg"].libs = ["bimg"]
        self.cpp_info.components["bimg"].requires = ["bx", "miniz::miniz"]

        if not self.options.shared:
            self.cpp_info.components["decode"].set_property("cmake_target_name", "bgfx::bimg_decode")
            self.cpp_info.components["decode"].libs = ["bimg_decode"]
            self.cpp_info.components["decode"].requires = ["bx", "miniz::miniz", "tinyexr::tinyexr", "lodepng::lodepng"]

            self.cpp_info.components["encode"].set_property("cmake_target_name", "bgfx::bimg_encode")
            self.cpp_info.components["encode"].libs = ["bimg_encode"]
            self.cpp_info.components["encode"].requires = ["bx", "libsquish::libsquish", "tinyexr::tinyexr"]

        self.cpp_info.components["bgfx"].set_property("cmake_target_name", "bgfx::bgfx")
        self.cpp_info.components["bgfx"].libs = ["bgfx"]
        self.cpp_info.components["bgfx"].requires = ["bx", "bimg"]
        if self.options.shared:
            self.cpp_info.components["bgfx"].defines.append("BGFX_SHARED_LIB_BUILD=1")
        if self.settings.os == "Linux":
            self.cpp_info.components["bgfx"].requires.extend(["xorg::xorg", "opengl::opengl", "wayland::wayland"])
        elif is_apple_os(self):
            self.cpp_info.components["bgfx"].frameworks = ["Cocoa", "Metal", "QuartzCore", "IOKit", "CoreFoundation"]
        # multithreaded rendering is enabled by default via BGFX_CONFIG_MULTITHREADED
        self.cpp_info.components["bgfx"].defines.extend([
            "BGFX_CONFIG_MULTITHREADED=1",
            f"BGFX_CONFIG_DEBUG_ANNOTATION={1 if self.settings.build_type == 'Debug' else 0}",
        ])

        if self.options.tools:
            for tool in ["bin2c", "texturec", "texturev", "geometryc", "geometryv", "shaderc"]:
                self.cpp_info.components[tool].set_property("cmake_target_name", f"bgfx::{tool}")
                # INFO: .exe requires CMakeConfigDeps generator
                self.cpp_info.components[tool].exe = os.path.join("bin", tool)
                self.cpp_info.components[tool].libdirs = []
                self.cpp_info.components[tool].includedirs = []
