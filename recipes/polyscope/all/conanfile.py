import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.31"


class PolyscopeConan(ConanFile):
    name = "polyscope"
    description = "A viewer for 3D data like meshes and point clouds"
    license = "MIT"
    homepage = "https://polyscope.run"
    topics = ("3d", "visualization", "meshes", "point-clouds")
    package_type = "library"
    provides = ["imguizmo"]
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "backend_glfw": [True, False],
        "backend_egl": [True, False],
        "backend_mock": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "backend_glfw": True,
        "backend_egl": True,
        "backend_mock": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def config_options(self):
        if self.settings.os == "Windows":
            # The project does not export the necessary symbols for a shared build
            self.package_type = "static-library"
            del self.options.shared
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.backend_egl

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.backend_glfw:
            self.requires("glfw/[^3.4]", transitive_headers=True, transitive_libs=True)
        if self.options.get_safe("backend_egl"):
            self.requires("egl/system", transitive_headers=True)
        if self.options.backend_glfw or self.options.get_safe("backend_egl"):
            self.requires("glad/0.1.36", transitive_headers=True, transitive_libs=True)
        self.requires("glm/[^1.0.1]", transitive_headers=True)
        self.requires("imgui/[^1.92.5]", transitive_headers=True, transitive_libs=True)
        self.requires("implot/[<2]", transitive_headers=True, transitive_libs=True)
        self.requires("nlohmann_json/[^3]")
        # Using a newer unvendored stb causes "undefined symbol" errors on Windows
        # self.requires("stb/[*]")

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        get(self, **self.conan_data["imguizmo_sources"][self.version],
            destination=os.path.join(self.source_folder, "deps", "imgui", "ImGuizmo"),
            strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_polyscope_INCLUDE"] = "conan_deps.cmake"
        tc.variables["POLYSCOPE_BACKEND_OPENGL3_GLFW"] = self.options.backend_glfw
        tc.variables["POLYSCOPE_BACKEND_OPENGL3_EGL"] = self.options.get_safe("backend_egl", False)
        tc.variables["POLYSCOPE_BACKEND_OPENGL_MOCK"] = self.options.backend_mock
        tc.variables["HAVE_EGL_LIB"] = self.options.get_safe("backend_egl", False)  # Skip EGL/egl.h check for libglvnd
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        if self.settings.os == "Windows" and not self.options.get_safe("shared"):
            # Avoid the default IMGUI_API=__declspec(dllimport)
            tc.preprocessor_definitions["IMGUI_API"] = None
        # #error "GLM: GLM_GTX_norm is an experimental extension and may change in the future.
        #         Use #define GLM_ENABLE_EXPERIMENTAL before including it, if you really want to use it."
        tc.preprocessor_definitions["GLM_ENABLE_EXPERIMENTAL"] = None
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("glad", "cmake_target_name", "glad")
        deps.set_property("glfw", "cmake_target_name", "glfw")
        deps.set_property("egl", "cmake_target_name", "EGL")
        deps.set_property("imgui", "cmake_target_name", "imgui")
        deps.generate()

    def _patch_sources(self):
        copy(self, "*",
             os.path.join(self.dependencies["imgui"].package_folder, "share", "imgui", "bindings"),
             os.path.join(self.source_folder, "include", "backends"))

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE",
             os.path.join(self.source_folder, "deps", "imgui", "ImGuizmo"),
             os.path.join(self.package_folder, "licenses", "imguizmo"))
        cmake = CMake(self)
        cmake.install()
        # Installed Polyscope backend headers include these as "backends/imgui_impl_*.h".
        copy(self, "*.h",
             os.path.join(self.source_folder, "include", "backends"),
             os.path.join(self.package_folder, "include", "backends"))

    def package_info(self):
        # The project does not define any CMake targets
        self.cpp_info.libs = ["polyscope"]
        self.cpp_info.requires = ["glm::glm", "imgui::core", "implot::implot"]
        if self.options.backend_glfw:
            self.cpp_info.requires.append("glfw::glfw")
        if self.options.backend_glfw or self.options.get_safe("backend_egl"):
            self.cpp_info.requires.append("glad::glad")
        if self.options.get_safe("backend_egl"):
            self.cpp_info.requires.append("egl::egl")
        # nlohmann_json is used only while compiling the library; no public header exposes it.
        self.cpp_info.ignored_requires = ["nlohmann_json"]
        self.cpp_info.defines.append("GLM_ENABLE_EXPERIMENTAL")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
        elif is_apple_os(self):
            self.cpp_info.frameworks = ["Cocoa", "OpenGL", "CoreVideo", "IOKit"]
