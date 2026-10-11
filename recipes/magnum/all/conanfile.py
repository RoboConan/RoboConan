import os
import textwrap

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class MagnumConan(ConanFile):
    name = "magnum"
    description = "Lightweight and modular C++11/C++14 graphics middleware for games and data visualization"
    license = "MIT"
    homepage = "https://magnum.graphics"
    topics = ("magnum", "graphics", "middleware", "graphics", "rendering", "gamedev", "opengl", "3d", "2d", "opengl", "game-engine", "pre-built")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "shared_plugins": [True, False],
        "build_deprecated": [True, False],
        # Follow documented build-options in https://doc.magnum.graphics/magnum/building.html#building-features
        #   Options like `with_xxxx` have been renamed to `xxxx`
        #   Options related to GL are being refactored into a choice option: gles2, gles3 or desktop_gl
        #   Option names are converted to snake_case
        "target_gl": ["gles2", "gles3", "desktop_gl", False],
        "target_egl": [True, False],
        "target_vk": [True, False],
        "audio": [True, False],
        "debug_tools": [True, False],
        "gl": [True, False],
        "material_tools": [True, False],
        "mesh_tools": [True, False],
        "primitives": [True, False],
        "scene_graph": [True, False],
        "scene_tools": [True, False],
        "shaders": [True, False],
        "shader_tools": [True, False],
        "text": [True, False],
        "texture_tools": [True, False],
        "trade": [True, False],
        "vk": [True, False],
        "android_application": [True, False],
        "emscripten_application": [True, False],
        "glfw_application": [True, False],
        "glx_application": [True, False],
        "sdl2_application": [True, False],
        "xegl_application": [True, False],
        "windowless_cgl_application": [True, False],
        "windowless_egl_application": [True, False],
        "windowless_glx_application": [True, False],
        "windowless_ios_application": [True, False],
        "windowless_wgl_application": [True, False],
        "cgl_context": [True, False],
        "egl_context": [True, False],
        "glx_context": [True, False],
        "wgl_context": [True, False],
        "gl_info": [True, False],
        "al_info": [True, False],
        "vk_info": [True, False],
        "distance_field_converter": [True, False],
        "font_converter": [True, False],
        "image_converter": [True, False],
        "scene_converter": [True, False],
        "shader_converter": [True, False],
        # Plugins
        "any_audio_importer": [True, False],
        "any_image_converter": [True, False],
        "any_image_importer": [True, False],
        "any_scene_converter": [True, False],
        "any_scene_importer": [True, False],
        "any_shader_converter": [True, False],
        "magnum_font": [True, False],
        "magnum_font_converter": [True, False],
        "obj_importer": [True, False],
        "tga_importer": [True, False],
        "tga_image_converter": [True, False],
        "wav_audio_importer": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "shared_plugins": True,
        "build_deprecated": True,
        "target_gl": "desktop_gl",
        "target_egl": True,
        "target_vk": True,
        "audio": True,
        "debug_tools": True,
        "gl": True,
        "material_tools": True,
        "mesh_tools": True,
        "primitives": True,
        "scene_graph": True,
        "scene_tools": True,
        "shaders": True,
        "shader_tools": True,
        "text": True,
        "texture_tools": True,
        "trade": True,
        "vk": True,
        "android_application": True,
        "emscripten_application": True,
        "glfw_application": True,
        "glx_application": True,
        "sdl2_application": True,
        "xegl_application": True,
        "windowless_cgl_application": True,
        "windowless_egl_application": True,
        "windowless_glx_application": True,
        "windowless_ios_application": True,
        "windowless_wgl_application": True,
        "cgl_context": True,
        "egl_context": True,
        "glx_context": True,
        "wgl_context": True,
        "gl_info": True,
        "al_info": True,
        "vk_info": True,
        "distance_field_converter": True,
        "font_converter": True,
        "image_converter": True,
        "scene_converter": True,
        "shader_converter": True,
        # Plugins
        "any_audio_importer": True,
        "any_image_converter": True,
        "any_image_importer": True,
        "any_scene_converter": True,
        "any_scene_importer": True,
        "any_shader_converter": True,
        "magnum_font": True,
        "magnum_font_converter": True,
        "obj_importer": True,
        "tga_importer": True,
        "tga_image_converter": True,
        "wav_audio_importer": True,
    }

    def config_options(self):
        if self.settings.os in ["Android", "Emscripten", "iOS"] and self.options.target_gl == "desktop_gl":
            self.options.target_gl = "gles3"

        # Doc says that 'distance_field_converter' is only available with "desktop GL" (the same is said for 'font_converter', but it builds)
        # TODO: Here we probably have a CHOICE OPTION
        if self.options.target_gl in ["gles2", "gles3"]:
            self.options.rm_safe("distance_field_converter")

        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
            self.options.rm_safe("egl_context")
            self.options.rm_safe("xegl_application")
            self.options.rm_safe("windowless_egl_application")
            self.options.rm_safe("windowless_ios_application")
            self.options.rm_safe("windowless_glx_application")
            self.options.rm_safe("target_egl")  # Requires EGL (when used gl_info)
            self.options.rm_safe("glx_application")
            self.options.rm_safe("glx_context")
            self.options.rm_safe("cgl_context")
            self.options.rm_safe("windowless_cgl_application")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.options.rm_safe("cgl_context")
            self.options.rm_safe("windowless_cgl_application")
            self.options.rm_safe("wgl_context")
            self.options.rm_safe("windowless_wgl_application")

        if self.settings.os == "Macos":
            self.options.rm_safe("egl_context")
            self.options.rm_safe("glx_application")  # Requires GL/glx.h (maybe XQuartz project)
            self.options.rm_safe("glx_context")
            self.options.rm_safe("xegl_application")
            self.options.rm_safe("windowless_egl_application")
            self.options.rm_safe("windowless_glx_application")  # Requires GL/glx.h (maybe XQuartz project)
            self.options.rm_safe("windowless_wgl_application")
            self.options.rm_safe("wgl_context")
            self.options.rm_safe("target_egl")  # Requires EGL (when used gl_info)

        if self.settings.os in ["Android", "Emscripten", "iOS"]:
            self.options.shared_plugins = False
            self.options.rm_safe("cgl_context")
            self.options.rm_safe("glfw_application")
            self.options.rm_safe("glx_application")
            self.options.rm_safe("glx_context")
            self.options.rm_safe("wgl_context")
            self.options.rm_safe("windowless_cgl_application")
            self.options.rm_safe("windowless_glx_application")
            self.options.rm_safe("windowless_wgl_application")
            self.options.rm_safe("xegl_application")

        if self.settings.os == "Android":
            self.options.rm_safe("sdl2_application")

        if self.settings.os in ["Android", "Emscripten"]:
            # Upstream enables EGL unconditionally on these targets.
            self.options.rm_safe("target_egl")

        if self.settings.os == "Emscripten":
            # Upstream does not declare Vulkan options for Emscripten.
            self.options.rm_safe("target_vk")
            self.options.rm_safe("vk")
            self.options.rm_safe("vk_info")
            self.options.rm_safe("font_converter")

        if self.settings.os != "Android":
            self.options.rm_safe("android_application")

        if self.settings.os != "Emscripten":
            self.options.rm_safe("emscripten_application")

        if self.settings.os != "iOS":
            self.options.rm_safe("windowless_ios_application")

    @property
    def _executables(self):
        # (executable, option name)
        all_execs = [
            ("gl-info", "gl_info"),
            ("al-info", "al_info"),
            ("vk-info", "vk_info"),
            ("distancefieldconverter", "distance_field_converter"),
            ("fontconverter", "font_converter"),
            ("imageconverter", "image_converter"),
            ("sceneconverter", "scene_converter"),
            ("shaderconverter", "shader_converter"),
        ]
        return [executable for executable, opt_name in all_execs if self.options.get_safe(opt_name)]

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _windowless_application(self):
        if not any(self.options.get_safe(option, False) for option in (
            "gl_info", "distance_field_converter", "font_converter",
        )):
            return None
        if self._target_egl:
            return "windowless_egl_application"
        if self.settings.os == "iOS":
            return "windowless_ios_application"
        if self.settings.os == "Macos":
            return "windowless_cgl_application"
        if self.settings.os in ["Linux", "FreeBSD"]:
            return "windowless_glx_application"
        if self.settings.os == "Windows":
            return "windowless_wgl_application"
        return None

    @property
    def _target_egl(self):
        if self.settings.os in ["Android", "Emscripten"]:
            return bool(self.options.gl)
        return bool(self.options.get_safe("target_egl", False))

    def _has_component(self, option):
        return bool(self.options.get_safe(option, False) or self._windowless_application == option)

    def requirements(self):
        # src/Magnum/Math/Vector.h#L37-L42
        self.requires("corrade/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.audio:
            # src/Magnum/Audio/Buffer.h#L46-L48
            # src/Magnum/Audio/CMakeLists.txt#L101-L104
            self.requires("openal-soft/[^1.22]", transitive_headers=True, transitive_libs=True)
        if self.options.gl:
            transitive_headers = self._has_component("windowless_glx_application")
            # src/Magnum/Platform/WindowlessGlxApplication.h#L44-L46
            # src/Magnum/GL/CMakeLists.txt#L222-L238
            self.requires("opengl/system", transitive_headers=transitive_headers, transitive_libs=True)
        if self.options.get_safe("vk", False):
            # src/Magnum/Vk/CMakeLists.txt#L183-L185
            self.requires("vulkan-loader/[^1.3.239.0]", transitive_libs=True)

        egl_headers = self._has_component("windowless_egl_application") or self.options.get_safe("android_application", False)
        egl_libs = (
            egl_headers
            or self.options.get_safe("egl_context", False)
            or self.options.get_safe("xegl_application", False)
            or self._target_egl and (
                self.options.get_safe("glfw_application", False)
                or self.options.get_safe("sdl2_application", False)
            )
        )
        if egl_libs and self.settings.os in ["Linux", "FreeBSD"]:
            # src/Magnum/Platform/WindowlessEglApplication.h#L37-L39
            # src/Magnum/Platform/CMakeLists.txt#L556
            self.requires("egl/system", transitive_headers=egl_headers, transitive_libs=True)

        x11_headers = any(self._has_component(option) for option in (
            "glx_application", "xegl_application", "windowless_glx_application",
        ))
        x11_libs = x11_headers or self.options.get_safe("glx_context", False)
        if x11_libs:
            # src/Magnum/Platform/AbstractXApplication.h#L42-L43
            # src/Magnum/Platform/CMakeLists.txt#L453-L467
            self.requires("xorg/system", transitive_headers=x11_headers, transitive_libs=True)

        if self.options.get_safe("glfw_application", False):
            # src/Magnum/Platform/GlfwApplication.h#L52
            # src/Magnum/Platform/CMakeLists.txt#L302-L309
            self.requires("glfw/[^3.4]", transitive_headers=True, transitive_libs=True)

        if self.options.get_safe("sdl2_application", False):
            # src/Magnum/Platform/Sdl2Application.h#L60-L64
            # src/Magnum/Platform/CMakeLists.txt#L367-L374
            self.requires("sdl/[^2.30.9]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 11)

        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "5.0":
            raise ConanInvalidConfiguration("GCC older than 5 is not supported (missing C++11 features)")

        if self.options.shared and not self.dependencies["corrade"].options.shared:
            # To fix issue with resource management, see here: https://github.com/mosra/magnum/issues/304#issuecomment-451768389
            raise ConanInvalidConfiguration("If using 'shared=True', corrade should be shared as well")

        if self.options.target_gl in ["gles2", "gles3"] and self.settings.os == "Macos":
            raise ConanInvalidConfiguration("OpenGL ES is not supported in Macos")

        if self.options.target_gl in ["gles2", "gles3"] and self.settings.os == "Windows":
            raise ConanInvalidConfiguration("OpenGL ES is not supported in Windows")

    def build_requirements(self):
        self.tool_requires("corrade/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["HUNTER_ENABLED"] = False
        tc.cache_variables["MAGNUM_BUILD_DEPRECATED"] = self.options.build_deprecated
        tc.cache_variables["MAGNUM_BUILD_STATIC"] = not self.options.shared
        tc.cache_variables["MAGNUM_BUILD_STATIC_PIC"] = self.options.get_safe("fPIC", False)
        corrade_options = self.dependencies["corrade"].options
        build_static_unique_globals = corrade_options.get_safe("build_static_unique_globals", "auto")
        if build_static_unique_globals != "auto":
            tc.cache_variables["MAGNUM_BUILD_STATIC_UNIQUE_GLOBALS"] = build_static_unique_globals
        static_unique_globals_dll_name = corrade_options.get_safe("static_unique_globals_dll_name")
        if static_unique_globals_dll_name:
            tc.cache_variables["MAGNUM_BUILD_STATIC_UNIQUE_GLOBALS_DLL_NAME"] = static_unique_globals_dll_name
        tc.cache_variables["MAGNUM_BUILD_PLUGINS_STATIC"] = not self.options.shared_plugins
        tc.cache_variables["MAGNUM_BUILD_TESTS"] = False
        tc.cache_variables["MAGNUM_BUILD_GL_TESTS"] = False
        tc.cache_variables["MAGNUM_BUILD_AL_TESTS"] = False
        tc.cache_variables["MAGNUM_BUILD_VK_TESTS"] = False
        tc.cache_variables["MAGNUM_TARGET_GL"] = bool(self.options.target_gl)
        tc.cache_variables["MAGNUM_TARGET_GLES"] = self.options.target_gl in ["gles2", "gles3"]
        tc.cache_variables["MAGNUM_TARGET_GLES2"] = self.options.target_gl == "gles2"
        tc.cache_variables["MAGNUM_TARGET_EGL"] = self._target_egl
        tc.cache_variables["MAGNUM_TARGET_VK"] = self.options.get_safe("target_vk", False)

        tc.cache_variables["MAGNUM_WITH_AUDIO"] = self.options.audio
        tc.cache_variables["MAGNUM_WITH_DEBUGTOOLS"] = self.options.debug_tools
        tc.cache_variables["MAGNUM_WITH_GL"] = self.options.gl
        tc.cache_variables["MAGNUM_WITH_MATERIALTOOLS"] = self.options.material_tools
        tc.cache_variables["MAGNUM_WITH_MESHTOOLS"] = self.options.mesh_tools
        tc.cache_variables["MAGNUM_WITH_PRIMITIVES"] = self.options.primitives
        tc.cache_variables["MAGNUM_WITH_SCENEGRAPH"] = self.options.scene_graph
        tc.cache_variables["MAGNUM_WITH_SCENETOOLS"] = self.options.scene_tools
        tc.cache_variables["MAGNUM_WITH_SHADERS"] = self.options.shaders
        tc.cache_variables["MAGNUM_WITH_SHADERTOOLS"] = self.options.shader_tools
        tc.cache_variables["MAGNUM_WITH_TEXT"] = self.options.text
        tc.cache_variables["MAGNUM_WITH_TEXTURETOOLS"] = self.options.texture_tools
        tc.cache_variables["MAGNUM_WITH_TRADE"] = self.options.trade
        tc.cache_variables["MAGNUM_WITH_VK"] = self.options.get_safe("vk", False)

        tc.cache_variables["MAGNUM_WITH_ANDROIDAPPLICATION"] = self.options.get_safe("android_application", False)
        tc.cache_variables["MAGNUM_WITH_EMSCRIPTENAPPLICATION"] = self.options.get_safe("emscripten_application", False)
        tc.cache_variables["MAGNUM_WITH_GLFWAPPLICATION"] = self.options.get_safe("glfw_application", False)
        tc.cache_variables["MAGNUM_WITH_GLXAPPLICATION"] = self.options.get_safe("glx_application", False)
        tc.cache_variables["MAGNUM_WITH_SDL2APPLICATION"] = self.options.get_safe("sdl2_application", False)
        tc.cache_variables["MAGNUM_WITH_XEGLAPPLICATION"] = self.options.get_safe("xegl_application", False)
        tc.cache_variables["MAGNUM_WITH_WINDOWLESSCGLAPPLICATION"] = self.options.get_safe("windowless_cgl_application", False)
        tc.cache_variables["MAGNUM_WITH_WINDOWLESSEGLAPPLICATION"] = self.options.get_safe("windowless_egl_application", False)
        tc.cache_variables["MAGNUM_WITH_WINDOWLESSGLXAPPLICATION"] = self.options.get_safe("windowless_glx_application", False)
        tc.cache_variables["MAGNUM_WITH_WINDOWLESSIOSAPPLICATION"] = self.options.get_safe("windowless_ios_application", False)
        tc.cache_variables["MAGNUM_WITH_WINDOWLESSWGLAPPLICATION"] = self.options.get_safe("windowless_wgl_application", False)

        tc.cache_variables["MAGNUM_WITH_CGLCONTEXT"] = self.options.get_safe("cgl_context", False)
        tc.cache_variables["MAGNUM_WITH_EGLCONTEXT"] = self.options.get_safe("egl_context", False)
        tc.cache_variables["MAGNUM_WITH_GLXCONTEXT"] = self.options.get_safe("glx_context", False)
        tc.cache_variables["MAGNUM_WITH_WGLCONTEXT"] = self.options.get_safe("wgl_context", False)

        ##### Plugins related #####
        tc.cache_variables["MAGNUM_WITH_ANYAUDIOIMPORTER"] = self.options.any_audio_importer
        tc.cache_variables["MAGNUM_WITH_ANYIMAGECONVERTER"] = self.options.any_image_converter
        tc.cache_variables["MAGNUM_WITH_ANYIMAGEIMPORTER"] = self.options.any_image_importer
        tc.cache_variables["MAGNUM_WITH_ANYSCENECONVERTER"] = self.options.any_scene_converter
        tc.cache_variables["MAGNUM_WITH_ANYSCENEIMPORTER"] = self.options.any_scene_importer
        tc.cache_variables["MAGNUM_WITH_ANYSHADERCONVERTER"] = self.options.any_shader_converter
        tc.cache_variables["MAGNUM_WITH_MAGNUMFONT"] = self.options.magnum_font
        tc.cache_variables["MAGNUM_WITH_MAGNUMFONTCONVERTER"] = self.options.magnum_font_converter
        tc.cache_variables["MAGNUM_WITH_OBJIMPORTER"] = self.options.obj_importer
        tc.cache_variables["MAGNUM_WITH_TGAIMPORTER"] = self.options.tga_importer
        tc.cache_variables["MAGNUM_WITH_TGAIMAGECONVERTER"] = self.options.tga_image_converter
        tc.cache_variables["MAGNUM_WITH_WAVAUDIOIMPORTER"] = self.options.wav_audio_importer

        #### Command line utilities ####
        tc.cache_variables["MAGNUM_WITH_GL_INFO"] = self.options.gl_info
        tc.cache_variables["MAGNUM_WITH_AL_INFO"] = self.options.al_info
        tc.cache_variables["MAGNUM_WITH_VK_INFO"] = self.options.get_safe("vk_info", False)
        tc.cache_variables["MAGNUM_WITH_DISTANCEFIELDCONVERTER"] = self.options.get_safe("distance_field_converter", False)
        tc.cache_variables["MAGNUM_WITH_FONTCONVERTER"] = self.options.font_converter
        tc.cache_variables["MAGNUM_WITH_IMAGECONVERTER"] = self.options.image_converter
        tc.cache_variables["MAGNUM_WITH_SCENECONVERTER"] = self.options.scene_converter
        tc.cache_variables["MAGNUM_WITH_SHADERCONVERTER"] = self.options.shader_converter

        tc.generate()

        tc = CMakeDeps(self)
        if "egl" in self.dependencies.host:
            tc.set_property("egl", "cmake_file_name", "EGL")
            tc.set_property("egl", "cmake_find_mode", "module")
            tc.set_property("egl", "cmake_target_name", "EGL::EGL")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _extract_cmake_shim(self) -> str:
        find_magnum = load(self, os.path.join(
            self.package_folder, "share", "cmake", "Magnum", "FindMagnum.cmake"))
        flags_begin = find_magnum.find("# Read flags from configuration")
        flags_end = find_magnum.find("# CMake module dir for dependencies", flags_begin)
        if flags_begin == -1 or flags_end == -1:
            raise ConanException("Unable to extract configuration variables from FindMagnum.cmake")
        configure_flags = find_magnum[flags_begin:flags_end]

        executable_components = " ".join(self._executables)
        shim = textwrap.dedent("""\
            # Generated from the packaged FindMagnum.cmake configuration-variable block.
            set(_MAGNUM_CONFIGURE_FILE
                "${CMAKE_CURRENT_LIST_DIR}/../../../include/Magnum/configure.h")
        """) + configure_flags + textwrap.dedent("""\
            set(_MAGNUM_DEPENDENCY_MODULE_DIR
                "${CMAKE_CURRENT_LIST_DIR}/../../cmake/Magnum/dependencies")
        """) + textwrap.dedent(f"""\

            # Match the imported executable targets provided by FindMagnum.cmake,
            # resolving them from the build environment so cross builds use the
            # native tool-require package instead of target executables.
            set(_MAGNUM_CONAN_EXECUTABLE_COMPONENTS {executable_components})
            foreach(_component IN LISTS _MAGNUM_CONAN_EXECUTABLE_COMPONENTS)
                unset(_MAGNUM_CONAN_EXECUTABLE CACHE)
                find_program(_MAGNUM_CONAN_EXECUTABLE
                    NAMES "magnum-${{_component}}"
                    PATHS ENV PATH
                    NO_DEFAULT_PATH)
                if(_MAGNUM_CONAN_EXECUTABLE AND NOT TARGET Magnum::${{_component}})
                    add_executable(Magnum::${{_component}} IMPORTED)
                    set_property(TARGET Magnum::${{_component}} PROPERTY
                        IMPORTED_LOCATION "${{_MAGNUM_CONAN_EXECUTABLE}}")
                endif()
            endforeach()
            unset(_MAGNUM_CONAN_EXECUTABLE CACHE)
            unset(_MAGNUM_CONAN_EXECUTABLE_COMPONENTS)
        """)
        return shim

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        shim = self._extract_cmake_shim()
        save(self, os.path.join(self.package_folder, "share", "conan", "magnum", "conan-magnum-vars.cmake"), shim)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "Magnum")
        self.cpp_info.set_property("cmake_build_modules", ["share/conan/magnum/conan-magnum-vars.cmake",])

        magnum_plugin_libdir = "magnum-d" if self.settings.build_type == "Debug" and self.options.shared_plugins else "magnum"
        plugin_lib_suffix = "-d" if self.settings.build_type == "Debug" and not self.options.shared_plugins else ""
        lib_suffix = "-d" if self.settings.build_type == "Debug" else ""

        def _add_component(component_name, lib_name, requires):
            component = self.cpp_info.components[component_name]
            component.set_property("cmake_target_name", f"Magnum::{lib_name}")
            component.libs = [f"Magnum{lib_name}{lib_suffix}"]
            component.requires = list(dict.fromkeys(requires + ["magnum_main"]))

        # Magnum contains just the main library
        magnum_main = self.cpp_info.components["magnum_main"]
        magnum_main.set_property("cmake_target_name", "Magnum::Magnum")
        magnum_main.libs = [f"Magnum{lib_suffix}"]
        magnum_main.requires = ["corrade::utility"]

        if self.options.audio:
            _add_component("audio", "Audio", ["magnum_main", "corrade::plugin_manager", "openal-soft::openal-soft"])
            if self.options.scene_graph:
                self.cpp_info.components["audio"].requires += ["scene_graph"]
        if self.options.debug_tools:
            _add_component("debug_tools", "DebugTools", ["magnum_main"])
            if self.options.trade:
                self.cpp_info.components["debug_tools"].requires.append("trade")
            if self.options.target_gl:
                self.cpp_info.components["debug_tools"].requires.append("gl")
        if self.options.gl:
            _add_component("gl", "GL", ["magnum_main", "opengl::opengl"])
        if self.options.material_tools:
            _add_component("material_tools", "MaterialTools", ["magnum_main", "trade"])
        if self.options.mesh_tools:
            _add_component("mesh_tools", "MeshTools", ["magnum_main", "trade"])
            if self.options.target_gl:
                self.cpp_info.components["mesh_tools"].requires.append("gl")
        if self.options.primitives:
            _add_component("primitives", "Primitives", ["magnum_main", "mesh_tools", "trade"])
        if self.options.scene_graph:
            _add_component("scene_graph", "SceneGraph", ["magnum_main"])
        if self.options.scene_tools:
            _add_component("scene_tools", "SceneTools", ["magnum_main", "trade"])
        if self.options.shaders:
            _add_component("shaders", "Shaders", ["magnum_main"])
            if self.options.target_gl:
                self.cpp_info.components["shaders"].requires.append("gl")
        if self.options.shader_tools:
            _add_component("shader_tools", "ShaderTools", ["magnum_main", "corrade::plugin_manager"])
        if self.options.text:
            _add_component("text", "Text", ["magnum_main", "texture_tools", "corrade::plugin_manager"])
            if self.options.target_gl:
                self.cpp_info.components["text"].requires.append("gl")
        if self.options.texture_tools:
            _add_component("texture_tools", "TextureTools", ["magnum_main"])
            if self.options.target_gl:
                self.cpp_info.components["texture_tools"].requires += ["gl"]
        if self.options.trade:
            _add_component("trade", "Trade", ["magnum_main", "corrade::plugin_manager"])
        if self.options.get_safe("vk", False):
            _add_component("vk", "Vk", ["magnum_main", "vulkan-loader::vulkan-loader"])

        egl_requirement = ["egl::egl"] if self.settings.os in ["Linux", "FreeBSD"] else []

        #### APPLICATIONS ####
        if self.options.get_safe("android_application", False):
            _add_component("android_application", "AndroidApplication", ["gl"] + egl_requirement)
        if self.options.get_safe("emscripten_application", False):
            _add_component("emscripten_application", "EmscriptenApplication", ["magnum_main"])
            if self.options.target_gl:
                self.cpp_info.components["emscripten_application"].requires.append("gl")
        if self.options.get_safe("windowless_ios_application", False):
            _add_component("windowless_ios_application", "WindowlessIosApplication", ["gl"])
        if self.options.get_safe("glx_application", False):
            _add_component("glx_application", "GlxApplication", ["gl", "xorg::x11"])
        if self.options.get_safe("glfw_application", False):
            _add_component("glfw_application", "GlfwApplication", ["magnum_main", "glfw::glfw"])
            if self.options.target_gl:
                self.cpp_info.components["glfw_application"].requires.append("gl")
            if self._target_egl:
                self.cpp_info.components["glfw_application"].requires += egl_requirement
        if self.options.get_safe("sdl2_application", False):
            _add_component("sdl2_application", "Sdl2Application", ["magnum_main", "sdl::sdl"])
            if self.options.target_gl:
                self.cpp_info.components["sdl2_application"].requires += ["gl"]
            if self._target_egl:
                self.cpp_info.components["sdl2_application"].requires += egl_requirement
        if self.options.get_safe("xegl_application", False):
            _add_component("xegl_application", "XEglApplication", ["gl", "xorg::x11"] + egl_requirement)
        if self._has_component("windowless_cgl_application"):
            _add_component("windowless_cgl_application", "WindowlessCglApplication", ["gl"])
        if self._has_component("windowless_egl_application"):
            _add_component("windowless_egl_application", "WindowlessEglApplication", ["gl"] + egl_requirement)
        if self._has_component("windowless_glx_application"):
            _add_component("windowless_glx_application", "WindowlessGlxApplication", ["gl", "xorg::x11"])
        if self._has_component("windowless_wgl_application"):
            _add_component("windowless_wgl_application", "WindowlessWglApplication", ["gl"])
        #### CONTEXTS ####
        if self.options.get_safe("cgl_context", False):
            _add_component("cgl_context", "CglContext", ["gl"])
        if self.options.get_safe("egl_context", False):
            _add_component("egl_context", "EglContext", ["gl"] + egl_requirement)
        if self.options.get_safe("glx_context", False):
            _add_component("glx_context", "GlxContext", ["gl", "xorg::x11"])
        if self.options.get_safe("wgl_context", False):
            _add_component("wgl_context", "WglContext", ["gl"])

        ######## PLUGINS ########
        for component, lib_name, folder, deps in self._plugins:
            self.cpp_info.components[component].set_property("cmake_target_name", f"Magnum::{lib_name}")
            # add only static plugins: shared plugins are meant to be loaded dynamically and not to be used during linking
            if not self.options.shared_plugins:
                self.cpp_info.components[component].libs = [f"{lib_name}{plugin_lib_suffix}"]
            self.cpp_info.components[component].libdirs = [os.path.join("lib", magnum_plugin_libdir, folder)]
            self.cpp_info.components[component].requires = deps

        plugin_dir = "bin" if self.settings.os == "Windows" else "lib"
        plugins_basepath = os.path.join(self.package_folder, plugin_dir, magnum_plugin_libdir)
        self.conf_info.define("user.magnum:plugins_basepath", plugins_basepath)

    @property
    def _plugins(self):
        # (component, lib_name, folder, deps)
        plugins = [
            ("any_audio_importer", "AnyAudioImporter", "audioimporters", ["magnum_main", "audio"]),
            ("any_image_converter", "AnyImageConverter", "imageconverters", ["trade"]),
            ("any_image_importer", "AnyImageImporter", "importers", ["trade"]),
            ("any_scene_converter", "AnySceneConverter", "sceneconverters", ["trade"]),
            ("any_scene_importer", "AnySceneImporter", "importers", ["trade"]),
            ("any_shader_converter", "AnyShaderConverter", "shaderconverters", ["shader_tools"]),
            ("magnum_font", "MagnumFont", "fonts", ["trade", "tga_importer", "gl", "text", "texture_tools"]),
            ("magnum_font_converter", "MagnumFontConverter", "fontconverters", ["trade", "tga_image_converter", "text", "texture_tools"]),
            ("obj_importer", "ObjImporter", "importers", ["trade", "mesh_tools"]),
            ("tga_importer", "TgaImporter", "importers", ["trade"]),
            ("tga_image_converter", "TgaImageConverter", "imageconverters", ["trade"]),
            ("wav_audio_importer", "WavAudioImporter", "audioimporters", ["magnum_main", "audio"]),
        ]
        return [plugin for plugin in plugins if self.options.get_safe(plugin[0])]
