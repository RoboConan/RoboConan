import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime, is_msvc

required_conan_version = ">=2.1"


class DiligentEngineConan(ConanFile):
    name = "diligent-engine"
    description = "Diligent Engine is a modern cross-platform low-level graphics library and rendering framework."
    license = "Apache-2.0 AND NCSA AND MIT"
    homepage = "https://github.com/DiligentGraphics/DiligentEngine"
    topics = ("graphics", "graphics-engine", "gamedev", "rendering", "ray-tracing")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "enable_archiver": [True, False],
        "enable_render_state_packager": [True, False],
        "with_glslang": [True, False],
    }
    default_options = {
        "enable_archiver": True,
        "enable_render_state_packager": False,
        "with_glslang": False,
    }

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def package_id(self):
        if is_msvc(self.info):
            if is_msvc_static_runtime(self.info):
                self.info.settings.compiler.runtime = "MT/MTd"
            else:
                self.info.settings.compiler.runtime = "MD/MDd"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("opengl/system")
        if self.settings.os in ["Linux", "FreeBSD", "Macos", "Windows"]:
            self.requires("glew/2.2.0")
        self.requires("spirv-headers/[^1.3.239.0]")
        self.requires("spirv-cross/[^1.3.239.0]", options={"shared": False})
        self.requires("spirv-tools/[^1.3.239.0]")
        if self.options.with_glslang:
            self.requires("glslang/[^1.3.239.0]")
        self.requires("vulkan-headers/[^1.3.239.0]")
        self.requires("vulkan-validationlayers/[^1.3.239.0]")
        self.requires("volk/[^1.3.239.0]")
        self.requires("xxhash/[>=0.8.1 <0.9]")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.requires("xorg/system")
        # TODO: unvendor DirectXShaderCompiler headers?
        # TODO: unvendor DXBCChecksum from FidelityFX-SDK?

        # DiligentTools
        self.requires("imgui/[^1]", transitive_headers=True, transitive_libs=True)
        self.requires("imguizmo/1.83+git.20231114")
        self.requires("libpng/[~1.6]")
        self.requires("libtiff/[>=4.5 <5]")
        self.requires("nlohmann_json/[^3.11]")
        self.requires("stb/[*]")
        self.requires("taywee-args/6.4.6")
        self.requires("tinygltf/2.9.0")
        self.requires("zlib-ng/[^2.0]")
        self.requires("libjpeg-meta/latest")

    def validate(self):
        check_min_cppstd(self, 14)
        if is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration("Visual Studio build with MT runtime is not supported")
        if self._diligent_platform is None:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.dependencies["spirv-cross"].options.get_safe("shared"):
            # Shared spirv-cross does not export a C++ API
            raise ConanInvalidConfiguration("spirv-cross must be built as static")

    def build_requirements(self):
        self.tool_requires("cmake/[^4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["engine"], strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["core"], strip_root=True, destination="DiligentCore")
        get(self, **self.conan_data["sources"][self.version]["tools"], strip_root=True, destination="DiligentTools")
        get(self, **self.conan_data["sources"][self.version]["fx"], strip_root=True, destination="DiligentFX")

        apply_conandata_patches(self)

        with chdir(self, "DiligentCore"):
            # Remove vendored libs, except for two minor ones without a Conan package
            third_party = Path("ThirdParty")
            third_party.joinpath("CMakeLists.txt").write_text("")
            for path in third_party.iterdir():
                if path.is_dir() and path.name not in ["DirectXShaderCompiler", "GPUOpenShaderUtils"]:
                    rmdir(self, path)
            # Always install core files: fix android and emscripten installations
            replace_in_file(self, "CMakeLists.txt",
                            "set(DILIGENT_INSTALL_CORE OFF)",
                            "set(DILIGENT_INSTALL_CORE ON)")

        with chdir(self, "DiligentTools"):
            rmdir(self, "ThirdParty")
            save(self, os.path.join("ThirdParty", "CMakeLists.txt"), "")
            # Handle vendored imguizmo correctly
            replace_in_file(self, os.path.join("Imgui", "CMakeLists.txt"),
                            "source_group(",
                            "# source_group(")
            # Use a more robust target from FindX11.cmake for xcb
            replace_in_file(self, os.path.join("NativeApp", "CMakeLists.txt"),
                            "find_library(XCB_LIBRARY xcb)",
                            "set(XCB_LIBRARY X11::xcb)")

    @property
    def _diligent_platform(self):
        return {
            "Android": "PLATFORM_ANDROID",
            "Emscripten": "PLATFORM_EMSCRIPTEN",
            "Linux": "PLATFORM_LINUX",
            "Macos": "PLATFORM_MACOS",
            "Windows": "PLATFORM_WIN32",
            "iOS": "PLATFORM_IOS",
            "watchOS": "PLATFORM_TVOS",
        }.get(str(self.settings.os))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_DiligentEngine_INCLUDE"] = "conan_deps.cmake"
        tc.cache_variables["BUILD_SHARED_LIBS"] = False  # both static and shared are always built
        tc.cache_variables["DILIGENT_BUILD_SAMPLES"] = False
        tc.cache_variables["DILIGENT_NO_FORMAT_VALIDATION"] = True
        tc.cache_variables["DILIGENT_BUILD_TESTS"] = False
        tc.cache_variables["DILIGENT_NO_DXC"] = True
        tc.cache_variables["DILIGENT_NO_GLSLANG"] = not self.options.with_glslang
        tc.cache_variables["DILIGENT_USE_SPIRV_TOOLCHAIN"] = True
        tc.cache_variables["DILIGENT_CLANG_COMPILE_OPTIONS"] = ""
        tc.cache_variables["DILIGENT_MSVC_COMPILE_OPTIONS"] = ""
        tc.cache_variables["DILIGENT_INSTALL_PDB"] = False
        tc.cache_variables["ENABLE_RTTI"] = True
        tc.cache_variables["ENABLE_EXCEPTIONS"] = True
        tc.cache_variables[self._diligent_platform] = True
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.19"
        tc.cache_variables["SPIRV_CROSS_NAMESPACE_OVERRIDE"] = self.dependencies["spirv-cross"].options.namespace

        # Tools
        tc.cache_variables["DILIGENT_BUILD_TOOLS_TESTS"] = False
        tc.cache_variables["DILIGENT_BUILD_TOOLS_INCLUDE_TEST"] = False
        tc.cache_variables["DILIGENT_NO_RENDER_STATE_PACKAGER"] = not self.options.enable_render_state_packager
        tc.cache_variables["ARCHIVER_SUPPORTED"] = not self.options.enable_archiver
        tc.cache_variables["GL_SUPPORTED"] = True
        tc.cache_variables["GLES_SUPPORTED"] = True
        tc.cache_variables["VULKAN_SUPPORTED"] = True
        tc.cache_variables["METAL_SUPPORTED"] = is_apple_os(self)
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("glew", "cmake_target_name", "GLEW::glew")
        deps.generate()

    def build(self):
        copy(self, "*",
             os.path.join(self.dependencies["imgui"].package_folder, "share", "imgui"),
             os.path.join(self.source_folder, "DiligentTools", "Imgui", "src", "backends"))
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        rename(self, os.path.join(self.package_folder, "Licenses"), os.path.join(self.package_folder, "licenses"))
        copy(self, "*/License.txt", os.path.join(self.source_folder, "DiligentCore", "ThirdParty"), os.path.join(self.package_folder, "licenses"), keep_path=True)

        # Flatten the lib and bin dirs, which by default have a lib/DiligentCore/Release etc structure
        rename(self, os.path.join(self.package_folder, "bin"), os.path.join(self.build_folder, "bin_orig"))
        rename(self, os.path.join(self.package_folder, "lib"), os.path.join(self.build_folder, "lib_orig"))
        copy(self, "*", os.path.join(self.build_folder, "bin_orig"), os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*", os.path.join(self.build_folder, "lib_orig"), os.path.join(self.package_folder, "lib"), keep_path=False)

        # Move *.fxh shaders since DiligentFX expects #include <Shaders/...> to work
        rename(self, os.path.join(self.package_folder, "Shaders"), os.path.join(self.package_folder, "include", "Shaders"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "DiligentEngine")

        core = self.cpp_info.components["DiligentCore"]
        core.set_property("cmake_target_name", "DiligentCore-static")
        core.libs = ["DiligentCore"]
        core.defines.append(f"{self._diligent_platform}=1")
        core.defines.append(f"DILIGENT_SPIRV_CROSS_NAMESPACE={self.dependencies['spirv-cross'].options.namespace}")
        if self.settings.os in ["Linux", "FreeBSD"]:
            core.system_libs = ["dl", "pthread"]
        elif self.settings.os == "Macos":
            core.frameworks = ["CoreFoundation", "Cocoa", "AppKit"]
        elif self.settings.os == "Windows":
            core.system_libs = ["dxgi", "shlwapi"]
        elif self.settings.os == "Android":
            core.system_libs = ["android", "log", "GLESv3", "EGL"]
        elif self.settings.os == "iOS":
            core.system_libs = ["OpenGLES"]
        core.requires = [
            "opengl::opengl",
            "glew::glew",
            "spirv-headers::spirv-headers",
            "spirv-cross::spirv-cross",
            "spirv-tools::spirv-tools",
            "vulkan-headers::vulkan-headers",
            "vulkan-validationlayers::vulkan-validationlayers",
            "volk::volk",
            "xxhash::xxhash",
        ]
        if self.settings.os in ["Linux", "FreeBSD", "Macos", "Windows"]:
            core.requires.append("glew::glew")
        if self.options.with_glslang:
            core.requires.append("glslang::glslang")
        if self.settings.os in ["Linux", "FreeBSD"]:
            core.requires.append("xorg::x11")

        tools = self.cpp_info.components["DiligentTools"]
        tools.set_property("cmake_target_name", "DiligentTools-static")
        tools.libs = ["DiligentTools"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            tools.system_libs = ["dl", "pthread"]
        elif is_apple_os(self):
            tools.frameworks = ["CoreFoundation", "Cocoa"]
        tools.requires = [
            "DiligentCore",
            "imgui::imgui",
            "imguizmo::imguizmo",
            "libpng::libpng",
            "libtiff::libtiff",
            "nlohmann_json::nlohmann_json",
            "stb::stb",
            "taywee-args::taywee-args",
            "tinygltf::tinygltf",
            "zlib-ng::zlib-ng",
            "libjpeg-meta::jpeg",
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            tools.requires.extend([
                "xorg::x11",
                "xorg::xcb",
            ])

        fx = self.cpp_info.components["DiligentFX"]
        fx.set_property("cmake_target_name", "DiligentFX")
        fx.libs = ["DiligentFX"]
        fx.requires = [
            "DiligentCore",
            "DiligentTools",
        ]
