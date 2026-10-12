import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class OpenXRConan(ConanFile):
    name = "openxr"
    description = (
        "OpenXR is a royalty-free, open standard that provides a common set of APIs "
        "for developing XR applications that run across a wide range of AR and VR devices."
    )
    license = "Apache-2.0"
    homepage = "https://www.khronos.org/openxr/"
    topics = ("augmented-reality", "virtual-reality", "vr", "xr")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_loader": [True, False],
        "exceptions": [True, False],
        "with_opengl": [True, False],
        "with_opengles": [True, False],
        "with_vulkan": [True, False],
        "with_metal": [True, False],
        "presentation_backend": ["xlib", "xcb", "wayland"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_loader": True,
        "exceptions": True,
        "with_opengl": True,
        "with_opengles": True,
        "with_vulkan": True,
        "with_metal": True,
        "presentation_backend": "xlib",
    }
    implements = ["auto_shared_fpic"]

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        # https://github.com/KhronosGroup/OpenXR-SDK/blob/release-1.1.47/src/CMakeLists.txt#L51-L72
        if is_apple_os(self):
            del self.options.with_opengl
        else:
            del self.options.with_metal
        if self.settings.os == "Android":
            del self.options.with_opengl
            if int(self.settings.os.api_level.value) < 24:
                del self.options.with_vulkan
        else:
            del self.options.with_opengles
        if self.settings.os != "Linux":
            del self.options.presentation_backend

    def configure(self):
        if not self.options.build_loader:
            self.package_type = "header-library"
            self.options.rm_safe("shared")
            self.options.rm_safe("fPIC")
            self.options.rm_safe("exceptions")
            self.options.rm_safe("with_opengl")
            self.options.rm_safe("with_opengles")
            self.options.rm_safe("with_vulkan")
            self.options.rm_safe("with_metal")
            self.options.rm_safe("presentation_backend")

    def package_id(self):
        if not self.info.options.build_loader:
            self.info.clear()

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.build_loader:
            self.requires("jsoncpp/[^1.9.6]")
            if self.options.get_safe("with_opengl"):
                self.requires("opengl/system")
            if self.options.get_safe("with_opengles"):
                self.requires("egl/system")
            if self.options.get_safe("with_vulkan"):
                self.requires("vulkan-loader/[^1.3.239.0]")
            if self.settings.os == "Linux":
                if self.options.presentation_backend in ["xlib", "xcb"]:
                    self.requires("xorg/system")
                    if not self.options.get_safe("with_opengl"):
                        self.requires("opengl/system")
                else:
                    self.requires("wayland/[^1.22.0]")

    def validate(self):
        check_min_cppstd(self, 14)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_LOADER"] = self.options.build_loader
        if self.options.build_loader:
            tc.cache_variables["DYNAMIC_LOADER"] = self.options.shared
            tc.cache_variables["BUILD_LOADER_WITH_EXCEPTION_HANDLING"] = self.options.exceptions
            tc.cache_variables["BUILD_TESTS"] = False
            tc.cache_variables["BUILD_CONFORMANCE_TESTS"] = False
            tc.cache_variables["BUILD_WITH_SYSTEM_JSONCPP"] = True
            tc.cache_variables["OPENXR_DEBUG_POSTFIX"] = ""
            for opt, pkg in [
                ("with_opengl", "OpenGL"),
                ("with_opengles", "OpenGLES"),
                ("with_opengles", "EGL"),
                ("with_vulkan", "Vulkan"),
                ("with_metal", "MetalTools"),
            ]:
                tc.cache_variables[f"CMAKE_DISABLE_FIND_PACKAGE_{pkg}"] = not self.options.get_safe(opt, False)
            if self.settings.os == "Linux":
                tc.cache_variables["PRESENTATION_BACKEND"] = self.options.presentation_backend
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        if not self.options.build_loader:
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"), "add_subdirectory(src)", "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenXR")
        self.cpp_info.set_property("pkg_config_name", "openxr")

        if self.options.build_loader:
            loader = self.cpp_info.components["openxr_loader"]
            loader.set_property("cmake_target_name", "OpenXR::openxr_loader")
            loader.libs = ["openxr_loader"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                loader.system_libs.extend(["m", "pthread", "dl"])
            loader.requires = ["jsoncpp::jsoncpp"]
            if self.options.get_safe("with_opengl"):
                loader.requires.append("opengl::opengl")
            if self.options.get_safe("with_opengles"):
                loader.requires.append("egl::egl")
                loader.system_libs.extend(["GLESv2", "GLESv3"])
            if self.options.get_safe("with_vulkan"):
                loader.requires.append("vulkan-loader::vulkan-loader")
            if self.settings.os == "Linux":
                match self.options.presentation_backend:
                    case "xlib":
                        loader.requires.extend(["xorg::x11", "xorg::xrandr", "xorg::xxf86vm", "opengl::opengl"])
                    case "xcb":
                        loader.requires.extend(["xorg::xcb", "xorg::xcb-glx", "opengl::opengl"])
                    case "wayland":
                        loader.requires.extend(["wayland::wayland-client", "wayland::wayland-egl"])

        self.cpp_info.components["headers"].set_property("cmake_target_name", "OpenXR::headers")
