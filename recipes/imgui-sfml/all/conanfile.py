import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class ImGuiSFMLConan(ConanFile):
    name = "imgui-sfml"
    description = "ImGui-SFML integrates Dear ImGui with SFML, enabling easy creation of GUIs for SFML applications."
    license = "MIT"
    homepage = "https://github.com/SFML/imgui-sfml"
    topics = ("gui", "graphical", "sfml", "imgui")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "disable_obsolete_functions": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "disable_obsolete_functions": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("sfml/[^3.0]", transitive_headers=True)
        self.requires("imgui/[^1.91.1]", transitive_headers=True)
        self.requires("opengl/system")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")

    def validate(self):
        check_min_cppstd(self, 17)
        if not self.dependencies["sfml"].options.graphics:
            raise ConanInvalidConfiguration('imgui-sfml requires -o="sfml/*:graphics=True"')

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["IMGUI_SFML_FIND_SFML"] = True
        tc.cache_variables["IMGUI_DIR"] = "UNUSED"
        tc.cache_variables["IMGUI_SFML_DISABLE_OBSOLETE_FUNCTIONS"] = self.options.disable_obsolete_functions
        tc.cache_variables["IMGUI_SFML_BUILD_TESTING"] = False
        tc.cache_variables["IMGUI_SFML_BUILD_EXAMPLES"] = False
        tc.generate()

        tc = CMakeDeps(self)
        tc.set_property("imgui", "cmake_file_name", "ImGui")
        tc.set_property("imgui", "cmake_additional_variables_prefixes", ["IMGUI"])
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ImGui-SFML")
        self.cpp_info.set_property("cmake_target_name", "ImGui-SFML::ImGui-SFML")

        postfix = ""
        if self.options.shared and self.settings.build_type == "Debug":
            postfix = "_d"
        self.cpp_info.libs = ["ImGui-SFML" + postfix]
        self.cpp_info.requires = ["sfml::graphics", "imgui::core", "opengl::opengl"]

        if self.options.disable_obsolete_functions:
            self.cpp_info.defines = ["IMGUI_DISABLE_OBSOLETE_FUNCTIONS"]
