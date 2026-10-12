import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class GlfwConan(ConanFile):
    name = "glfw"
    description = "GLFW is a free, Open Source, multi-platform library for OpenGL, OpenGL ES and Vulkan" \
                  "application development. It provides a simple, platform-independent API for creating" \
                  "windows, contexts and surfaces, reading input, handling events, etc."
    license = "Zlib"
    homepage = "https://github.com/glfw/glfw"
    topics = ("graphics", "opengl", "vulkan", "opengl-es")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "vulkan_static": [True, False],
        "with_x11": [True, False],
        "with_wayland": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "vulkan_static": False,
        "with_x11": True,
        "with_wayland": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if self.settings.os != "Linux":
            self.options.rm_safe("with_wayland")
        if self.settings.os not in ["Linux", "FreeBSD"] or Version(self.version) <= "3.3.8":
            self.options.rm_safe("with_x11")
        if Version(self.version) >= "3.4":
            self.options.rm_safe("vulkan_static")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

        if self.options.get_safe("with_wayland"):
            self.options["xkbcommon"].with_wayland = True
            self.options["wayland"].shared = True
            self.options["xkbcommon"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # libs=False because glfw does not link to opengl, it
        # loads it via dlopen or equivalent
        self.requires("opengl/system", libs=False, transitive_headers=True)
        if self.options.get_safe("vulkan_static"):
            self.requires("vulkan-loader/[^1.3.239.0]")
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.options.get_safe("with_x11", True):
                self.requires("xorg/system", libs=False)
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22.0]")
            self.requires("xkbcommon/[^1.6.0]")

    def validate(self):
        if self.options.get_safe("with_wayland"):
            xkbcommon_options = self.dependencies["xkbcommon"].options
            if not xkbcommon_options.with_wayland:
                raise ConanInvalidConfiguration(f"{self.ref} requires the with_wayland option in xkbcommon to be enabled when the with_wayland option is enabled")
            if not xkbcommon_options.shared:
                raise ConanInvalidConfiguration(f"{self.ref} always loads xkbcommon dependencies dynamically and does not support static linkage")
            if not self.dependencies["wayland"].options.shared:
                raise ConanInvalidConfiguration(f"{self.ref} always loads wayland dependencies dynamically and does not support static linkage")

    def build_requirements(self):
        if self.options.get_safe("with_wayland"):
            self.tool_requires("wayland/<host_version>")
            if not self.conf.get("tools.gnu:pkg_config", check_type=str):
                self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Fix X11 transitive deps not being propagated via specific include dirs vars
        cmakelists = "CMakeLists.txt" if Version(self.version) < "3.4" else "src/CMakeLists.txt"
        replace_in_file(self, cmakelists, "${X11_X11_INCLUDE_PATH}", "${X11_INCLUDE_DIR}")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["GLFW_BUILD_DOCS"] = False
        tc.cache_variables["GLFW_BUILD_EXAMPLES"] = False
        tc.cache_variables["GLFW_BUILD_TESTS"] = False
        tc.cache_variables["GLFW_INSTALL"] = True
        if Version(self.version) > "3.3.8":
            tc.cache_variables["GLFW_BUILD_X11"] = self.options.get_safe("with_x11", False)
            tc.cache_variables["GLFW_BUILD_WAYLAND"] = self.options.get_safe("with_wayland", False)
        else:
            tc.cache_variables["GLFW_USE_WAYLAND"] = self.options.get_safe("with_wayland", False)
        if Version(self.version) < "3.4":
            tc.cache_variables["GLFW_VULKAN_STATIC"] = self.options.get_safe("vulkan_static", False)
        if is_msvc(self):
            tc.cache_variables["USE_MSVC_RUNTIME_LIBRARY_DLL"] = not is_msvc_static_runtime(self)
        tc.generate()
        cmake_deps = CMakeDeps(self)
        if self.options.get_safe("with_wayland"):
            cmake_deps.set_property("xkbcommon", "cmake_file_name", "XKBCommon")
        cmake_deps.generate()
        if self.options.get_safe("with_wayland"):
            deps = PkgConfigDeps(self)
            deps.generate()

    def _patch_sources(self):
        # don't force PIC
        replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"),
                        "POSITION_INDEPENDENT_CODE ON", "")
        # don't force static link to libgcc if MinGW
        replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"),
                        "target_link_libraries(glfw PRIVATE \"-static-libgcc\")", "")

        # Allow to link vulkan-loader into shared glfw
        if self.options.get_safe("vulkan_static"):
            cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
            replace_in_file(
                self,
                cmakelists,
                'message(FATAL_ERROR "You are trying to link the Vulkan loader static library into the GLFW shared library")',
                "",
            )
            vulkan_lib = self.dependencies["vulkan-loader"].cpp_info.libs[0]
            replace_in_file(
                self,
                cmakelists,
                'list(APPEND glfw_PKG_DEPS "vulkan")',
                f'list(APPEND glfw_PKG_DEPS "vulkan")\nlist(APPEND glfw_LIBRARIES "{vulkan_lib}")',
            )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "glfw3")
        self.cpp_info.set_property("cmake_target_name", "glfw")
        self.cpp_info.set_property("pkg_config_name", "glfw3")
        libname = "glfw"
        if self.settings.os == "Windows" or not self.options.shared:
            libname += "3"
        if self.settings.os == "Windows" and self.options.shared:
            libname += "dll"
            self.cpp_info.defines.append("GLFW_DLL")
        self.cpp_info.libs = [libname]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "pthread", "dl", "rt"])
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs.append("gdi32")
        elif self.settings.os == "Macos":
            self.cpp_info.frameworks.extend([
                "AppKit", "Cocoa", "CoreFoundation", "CoreGraphics",
                "CoreServices", "Foundation", "IOKit",
            ])
        self.cpp_info.requires = ["opengl::opengl"]
        if self.options.get_safe("vulkan_static"):
            self.cpp_info.requires.append("vulkan-loader::vulkan-loader")
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.options.get_safe("with_x11", True):
                # https://github.com/glfw/glfw/blob/3.4/src/CMakeLists.txt#L181-L218
                # https://github.com/glfw/glfw/blob/3.3.2/CMakeLists.txt#L196-L233
                self.cpp_info.requires.extend([
                    "xorg::x11", # Also includes Xkb and Xshape
                    "xorg::xrandr",
                    "xorg::xinerama",
                    "xorg::xcursor",
                    "xorg::xi",
                ])
        if self.options.get_safe("with_wayland"):
            # https://github.com/glfw/glfw/blob/3.4/src/CMakeLists.txt#L163-L167
            self.cpp_info.requires.extend([
                "wayland::wayland-client",
                "wayland::wayland-cursor",
                "wayland::wayland-egl",
                "xkbcommon::xkbcommon"
            ])

        # Starting with version 3.4, glfw loads the platform libraries at runtime
        # and hence does not need to link with them.
        self.cpp_info.requires = []
        if Version(self.version) < "3.4":
            self.cpp_info.requires.append("opengl::opengl")
            if self.options.get_safe("vulkan_static"):
                self.cpp_info.requires.append("vulkan-loader::vulkan-loader")
            if self.settings.os in ["Linux", "FreeBSD"]:
                if self.options.get_safe("with_x11", True):
                    self.cpp_info.requires.append("xorg::x11")
            if self.options.get_safe("with_wayland"):
                self.cpp_info.requires.extend(["wayland::wayland", "xkbcommon::xkbcommon"])
