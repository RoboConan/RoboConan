import os
import re
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class ImguiConan(ConanFile):
    name = "imgui"
    description = "Bloat-free Immediate Mode Graphical User interface for C++ with minimal dependencies"
    license = "MIT"
    homepage = "https://github.com/ocornut/imgui"
    topics = ("gui", "graphical", "bloat-free")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "docking": [True, False],
        "enable_test_engine": [True, False],
        # Backends
        # See https://github.com/ocornut/imgui/blob/master/docs/BACKENDS.md
        "build_backends": [True, False],
        # "backend_allegro5": [True, False],
        "backend_android": [True, False],
        "backend_dx9": [True, False],
        "backend_dx10": [True, False],
        "backend_dx11": [True, False],
        "backend_dx12": [True, False],
        "backend_glfw": [True, False],
        "backend_glut": [True, False],
        "backend_metal": [True, False],
        "backend_opengl2": [True, False],
        "backend_opengl3": [True, False],
        "backend_osx": [True, False],
        "backend_sdl2": [True, False],
        "backend_sdlrenderer2": [True, False],
        "backend_sdl3": [True, False],
        "backend_sdlgpu3": [True, False],
        "backend_sdlrenderer3": [True, False],
        "backend_vulkan": [True, False],
        "backend_win32": [True, False],
        # "backend_wgpu": [True, False],
        # Other options
        # See https://github.com/ocornut/imgui/blob/master/imconfig.h for details
        "enable_freetype": [True, False],
        "enable_freetype_lunasvg": [True, False],
        "enable_metal_cpp": [True, False],
        "enable_osx_clipboard": [True, False],
        "enable_demo_windows": [True, False],
        "enable_debug_tools": [True, False],
        "use_bgra_packed_color": [True, False],
        "use_wchar32": [True, False],
        "build_programs": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "docking": False,
        "enable_test_engine": False,
        # Backends
        "build_backends": True,
        "backend_android": True,
        "backend_dx9": True,
        "backend_dx10": True,
        "backend_dx11": False,
        "backend_dx12": False,
        "backend_glfw": True,
        "backend_glut": False,
        "backend_metal": True,
        "backend_opengl2": True,
        "backend_opengl3": True,
        "backend_osx": True,
        "backend_sdl2": False,
        "backend_sdlrenderer2": False,
        "backend_sdl3": False,
        "backend_sdlgpu3": False,
        "backend_sdlrenderer3": False,
        "backend_vulkan": False,
        "backend_win32": True,
        # Other options
        "enable_freetype": False,
        "enable_freetype_lunasvg": False,
        "enable_metal_cpp": True,
        "enable_osx_clipboard": True,
        "enable_demo_windows": True,
        "enable_debug_tools": True,
        "use_bgra_packed_color": False,
        "use_wchar32": False,
        "build_programs": False,
    }

    @property
    def _using_sdl2(self):
        return any(self.options.get_safe(f"backend_{x}") for x in ["sdl2", "sdlrenderer2"])

    @property
    def _using_sdl3(self):
        return any(self.options.get_safe(f"backend_{x}") for x in ["sdl3", "sdlrenderer3", "sdlgpu3"])

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.version.endswith("-docking"):
            # Support the old -docking versions for backwards compatibility
            self.options.docking = True
        if self.settings.os != "Android":
            del self.options.backend_android
        if self.settings.os != "Windows":
            del self.options.backend_dx9
            del self.options.backend_dx10
            del self.options.backend_dx11
            del self.options.backend_dx12
            del self.options.backend_win32
        if not is_apple_os(self):
            del self.options.backend_metal
            del self.options.backend_osx
            del self.options.enable_metal_cpp
            del self.options.enable_osx_clipboard
        if Version(self.version) < "1.91.7":
            del self.options.backend_sdlgpu3
        if Version(self.version) < "1.90":
            del self.options.enable_freetype_lunasvg
        if Version(self.version) < "1.89.6":
            del self.options.backend_sdlrenderer2
            del self.options.backend_sdlrenderer3
        if Version(self.version) < "1.89.3":
            del self.options.backend_sdl2
            del self.options.backend_sdl3
        if Version(self.version) < "1.87":
            self.options.rm_safe("enable_metal_cpp")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.build_backends:
            self.options.rm_safe("backend_allegro5")
            self.options.rm_safe("backend_android")
            self.options.rm_safe("backend_dx9")
            self.options.rm_safe("backend_dx10")
            self.options.rm_safe("backend_dx11")
            self.options.rm_safe("backend_dx12")
            self.options.rm_safe("backend_glfw")
            self.options.rm_safe("backend_glut")
            self.options.rm_safe("backend_metal")
            self.options.rm_safe("backend_opengl2")
            self.options.rm_safe("backend_opengl3")
            self.options.rm_safe("backend_osx")
            self.options.rm_safe("backend_sdl2")
            self.options.rm_safe("backend_sdlrenderer2")
            self.options.rm_safe("backend_sdlrenderer3")
            self.options.rm_safe("backend_vulkan")
            self.options.rm_safe("backend_win32")
            self.options.rm_safe("backend_wgpu")
        if not self.options.enable_freetype:
            self.options.rm_safe("enable_freetype_lunasvg")
        if not self.options.get_safe("backend_osx"):
            self.options.rm_safe("enable_osx_clipboard")
        if not self.options.get_safe("backend_osx") and not self.options.get_safe("backend_metal"):
            self.options.rm_safe("enable_metal_cpp")

        if "test-engine" not in self.conan_data["sources"][self.version]:
            self.output.warning("No test engine found for this version, removing enable_test_engine option")
            del self.options.enable_test_engine

        if self.options.get_safe("enable_test_engine"):
            # Test engine is free for individuals, educational, open-source and small business uses. Paid for larger businesses.
            self.license = "MIT AND DocumentRef-LICENSE.imgui_test_engine.txt"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # if self.options.get_safe("backend_allegro5"):
        #     self.requires("allegro5/0")
        if self.options.get_safe("backend_opengl2") or self.options.get_safe("backend_opengl3"):
            self.requires("opengl/system")
        if self.options.get_safe("backend_glut") and self.settings.os != "Emscripten":
            self.requires("freeglut/[^3.4.0]")
        if self._using_sdl3:
            self.requires("sdl/[^3.1.8]", transitive_headers=self.options.get_safe("backend_sdlgpu3", False))
        elif self._using_sdl2:
            self.requires("sdl/[^2.0.17")
        if self.options.get_safe("backend_vulkan"):
            self.requires("vulkan-headers/[^1.3.239.0]", transitive_headers=True)
            self.requires("vulkan-loader/[^1.3.239.0]")
        if self.options.get_safe("backend_glfw") and self.settings.os != "Emscripten":
            self.requires("glfw/[^3.4]")
        # if self.options.get_safe("backend_wgpu"):
        #     self.requires("dawn/0.0+git.20240726")
        if self.options.enable_freetype:
            self.requires("freetype/[^2.13.2]")
            if self.options.get_safe("enable_freetype_lunasvg"):
                if Version(self.version) >= "1.92":
                    self.requires("lunasvg/[^3]")
                else:
                    self.requires("lunasvg/[^2]")
        if self.options.get_safe("enable_metal_cpp"):
            self.requires("metal-cpp/14.2", transitive_headers=bool(self.options.get_safe("backend_metal")))
        if self.options.get_safe("enable_test_engine"):
            self.requires("stb/[*]")

    def validate(self):
        check_min_cppstd(self, 11)
        if Version(self.version) < "1.89" and self.options.docking:
            raise ConanException("Docking support requires version 1.89 or newer.")
        if self._using_sdl2 and self._using_sdl3:
            raise ConanInvalidConfiguration("SDL2 and SDL3 backends cannot be enabled simultaneously")

    def source(self):
        # Handled in build() instead to support self.options.docking.
        pass

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["IMGUI_TEST_ENGINE"] = self.options.get_safe("enable_test_engine", False)
        tc.cache_variables["IMGUI_IMPL_ALLEGRO5"] = self.options.get_safe("backend_allegro5", False)
        tc.cache_variables["IMGUI_IMPL_ANDROID"] = self.options.get_safe("backend_android", False)
        tc.cache_variables["IMGUI_IMPL_DX9"] = self.options.get_safe("backend_dx9", False)
        tc.cache_variables["IMGUI_IMPL_DX10"] = self.options.get_safe("backend_dx10", False)
        tc.cache_variables["IMGUI_IMPL_DX11"] = self.options.get_safe("backend_dx11", False)
        tc.cache_variables["IMGUI_IMPL_DX12"] = self.options.get_safe("backend_dx12", False)
        tc.cache_variables["IMGUI_IMPL_GLFW"] = self.options.get_safe("backend_glfw", False)
        tc.cache_variables["IMGUI_IMPL_GLUT"] = self.options.get_safe("backend_glut", False)
        tc.cache_variables["IMGUI_IMPL_METAL"] = self.options.get_safe("backend_metal", False)
        tc.cache_variables["IMGUI_IMPL_OPENGL2"] = self.options.get_safe("backend_opengl2", False)
        tc.cache_variables["IMGUI_IMPL_OPENGL3"] = self.options.get_safe("backend_opengl3", False)
        tc.cache_variables["IMGUI_IMPL_OSX"] = self.options.get_safe("backend_osx", False)
        tc.cache_variables["IMGUI_IMPL_SDL2"] = self.options.get_safe("backend_sdl2", False)
        tc.cache_variables["IMGUI_IMPL_SDLRENDERER2"] = self.options.get_safe("backend_sdlrenderer2", False)
        tc.cache_variables["IMGUI_IMPL_SDL3"] = self.options.get_safe("backend_sdl3", False)
        tc.cache_variables["IMGUI_IMPL_SDLGPU3"] = self.options.get_safe("backend_sdlgpu3", False)
        tc.cache_variables["IMGUI_IMPL_SDLRENDERER3"] = self.options.get_safe("backend_sdlrenderer3", False)
        tc.cache_variables["IMGUI_IMPL_VULKAN"] = self.options.get_safe("backend_vulkan", False)
        tc.cache_variables["IMGUI_IMPL_WIN32"] = self.options.get_safe("backend_win32", False)
        tc.cache_variables["IMGUI_IMPL_WGPU"] = self.options.get_safe("backend_wgpu", False)
        tc.cache_variables["IMGUI_ENABLE_OSX_DEFAULT_CLIPBOARD_FUNCTIONS"] = self.options.get_safe("enable_osx_clipboard", False)
        tc.cache_variables["IMGUI_FREETYPE"] = self.options.enable_freetype
        tc.cache_variables["IMGUI_FREETYPE_LUNASVG"] = self.options.get_safe("enable_freetype_lunasvg", False)
        tc.cache_variables["IMGUI_BUILD_PROGRAMS"] = self.options.build_programs
        tc.cache_variables["IMGUI_IMPL_METAL_CPP"] = self.options.get_safe("enable_metal_cpp", False)
        tc.cache_variables["IMGUI_IMPL_METAL_CPP_EXTENSIONS"] = self.options.get_safe("enable_metal_cpp", False)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _source(self):
        with chdir(self, self.source_folder):
            kind = "docking" if self.options.docking else "regular"
            get(self, **self.conan_data["sources"][self.version][kind], strip_root=True)
            if self.options.get_safe("enable_test_engine"):
                test_engine = self.conan_data["sources"][self.version]["test-engine"]
                get(self, **test_engine, destination="test-engine", strip_root=True)
                rmdir(self, "test-engine/imgui_test_engine/thirdparty/stb")
            # Ensure the generated imgui_export.h is always included
            replace_in_file(self, "imgui.h",
                            '#include "imconfig.h"',
                            '#include "imconfig.h"\n\n#include "imgui_export.h"')
            if Version(self.version) >= "1.92":
                replace_in_file(self, "misc/freetype/imgui_freetype.cpp", "lunasvg.h", "lunasvg/lunasvg.h")

    def _configure_header(self):
        defines = {}
        defines["IMGUI_ENABLE_FREETYPE"] = self.options.enable_freetype
        defines["IMGUI_ENABLE_FREETYPE_LUNASVG"] = self.options.get_safe("enable_freetype_lunasvg")
        defines["IMGUI_ENABLE_OSX_DEFAULT_CLIPBOARD_FUNCTIONS"] = self.options.get_safe("enable_osx_clipboard")
        # Build default IME handler on MinGW as well, not just MSVC. Only disabled there due to a lack of autolinking support.
        defines["IMGUI_ENABLE_WIN32_DEFAULT_IME_FUNCTIONS"] = True
        defines["IMGUI_USE_BGRA_PACKED_COLOR"] = self.options.use_bgra_packed_color
        defines["IMGUI_USE_WCHAR32"] = self.options.use_wchar32
        defines["IMGUI_DISABLE_DEMO_WINDOWS"] = not self.options.enable_demo_windows
        if Version(self.version) >= "1.88":
            defines["IMGUI_DISABLE_DEBUG_TOOLS"] = not self.options.enable_debug_tools
        else:
            defines["IMGUI_DISABLE_METRICS_WINDOW"] = not self.options.enable_debug_tools

        imconfig_path = Path(self.source_folder, "imconfig.h")
        content = imconfig_path.read_text("utf8")
        for define, value in defines.items():
            if value:
                content, n = re.subn(rf"// *#define +{define}\b", f"#define {define}", content)
                if n != 1:
                    raise ConanException(f"Failed to set {define} in imconfig.h")
        # Not listed in imconfig.h, but supported by the OSX and Metal backends
        if self.options.get_safe("enable_metal_cpp"):
            content += "\n#define IMGUI_IMPL_METAL_CPP\n"
            content += "#define IMGUI_IMPL_METAL_CPP_EXTENSIONS\n"
        imconfig_path.write_text(content, "utf8")

    def build(self):
        self._source()
        self._configure_header()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.options.get_safe("enable_test_engine"):
            shutil.copy(os.path.join(self.source_folder, "test-engine", "imgui_test_engine", "LICENSE.txt"),
                        os.path.join(self.package_folder, "licenses", "LICENSE.imgui_test_engine.txt"))
        cmake = CMake(self)
        cmake.install()

        # Package ImGui sources for users that need more fine-grained control
        backends_folder = os.path.join(self.source_folder, "backends")
        res_folder = os.path.join(self.package_folder, "share", "imgui")
        copy(self, "imgui_impl_*", backends_folder, os.path.join(res_folder, "bindings"))
        copy(self, "imgui*.cpp", self.source_folder, os.path.join(res_folder, "src"))
        copy(self, "*", os.path.join(self.source_folder, "misc", "cpp"), os.path.join(res_folder, "misc", "cpp"))
        copy(self, "*", os.path.join(self.source_folder, "misc", "freetype"), os.path.join(res_folder, "misc", "freetype"))

    def package_info(self):
        # Unofficial aggregate target. Prefer the individual targets instead.
        self.cpp_info.set_property("cmake_target_name", "imgui::imgui_all")

        self.cpp_info.components["core"].set_property("cmake_target_name", "imgui::imgui")
        self.cpp_info.components["core"].set_property("pkg_config_name", "imgui")
        self.cpp_info.components["core"].libs = ["imgui"]
        self.cpp_info.components["core"].srcdirs = [os.path.join("share", "imgui", "bindings")]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["core"].system_libs.append("m")
        elif self.settings.os == "Windows":
            self.cpp_info.components["core"].system_libs.append("imm32")
        elif is_apple_os(self):
            if self.options.enable_osx_clipboard:
                self.cpp_info.components["core"].frameworks.append("ApplicationServices")
        if self.options.enable_freetype:
            self.cpp_info.components["core"].requires.append("freetype::freetype")
            if self.options.get_safe("enable_freetype_lunasvg"):
                self.cpp_info.components["core"].requires.append("lunasvg::lunasvg")
        if self.options.get_safe("enable_test_engine"):
            self.cpp_info.components["core"].includedirs.append(os.path.join("include", "imgui_test_engine"))
            self.cpp_info.components["core"].requires.append("stb::stb")

        def _add_binding(name, requires=None, system_libs=None, frameworks=None):
            if self.options.get_safe(f"backend_{name}"):
                self.cpp_info.components[name].libs = [f"imgui-{name}"]
                self.cpp_info.components[name].defines = [f"IMGUI_IMPL_{name.upper()}"]  # unofficial
                self.cpp_info.components[name].requires = ["core"]
                self.cpp_info.components[name].requires = requires or []
                self.cpp_info.components[name].system_libs = system_libs or []
                self.cpp_info.components[name].frameworks = frameworks or []

        def _metal_cpp():
            return ["metal-cpp::metal-cpp"] if self.options.get_safe("enable_metal_cpp") else []

        # _add_binding("allegro5", requires=["allegro::allegro"])
        _add_binding("android", system_libs=["android", "log", "EGL", "GLESv3"])
        _add_binding("dx9", system_libs=["d3d9"])
        _add_binding("dx10", system_libs=["d3d10"])
        _add_binding("dx11", system_libs=["d3d11"])
        _add_binding("dx12", system_libs=["d3d12"])
        _add_binding("glfw", requires=["glfw::glfw"] if self.settings.os != "Emscripten" else [])
        _add_binding("glut", requires=["freeglut::freeglut"] if self.settings.os != "Emscripten" else [])
        _add_binding("metal", frameworks=["Foundation", "Metal", "QuartzCore"], requires=_metal_cpp())
        _add_binding("opengl2", requires=["opengl::opengl"])
        _add_binding("opengl3", requires=["opengl::opengl"])
        _add_binding("osx", frameworks=["AppKit", "Carbon", "Cocoa", "Foundation", "GameController"], requires=_metal_cpp())
        _add_binding("sdl2", requires=["sdl::sdl"])
        _add_binding("sdlrenderer2", requires=["sdl::sdl"])
        _add_binding("sdl3", requires=["sdl::sdl"])
        _add_binding("sdlgpu3", requires=["sdl::sdl"])
        _add_binding("sdlrenderer3", requires=["sdl::sdl"])
        _add_binding("vulkan", requires=["vulkan-headers::vulkan-headers", "vulkan-loader::vulkan-loader"])
        _add_binding("win32", system_libs=["dwmapi", "xinput"])
        # _add_binding("wgpu", requires=["dawn::dawn"])

        self.conf_info.define("user.imgui:with_docking", bool(self.options.docking))
