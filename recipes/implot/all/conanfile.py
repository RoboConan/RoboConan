import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class ImplotConan(ConanFile):
    name = "implot"
    description = "Advanced 2D Plotting for Dear ImGui"
    license = "MIT"
    homepage = "https://github.com/epezent/implot"
    topics = ("imgui", "plot", "graphics", )
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
         "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    @property
    def _version_range(self):
        v = Version(self.version)
        if v >= "0.17":
            return "^1"
        if v >= "0.15":
            return "^1 <1.92"
        if v >= "0.14":
            return "^1 <1.91"
        if v >= "0.13":
            # imgui 1.89 renamed ImGuiKeyModFlags_* to  ImGuiModFlags_*
            return "^1 <1.90"
        return "^1 <1.87"

    def requirements(self):
        self.requires(f"imgui/[{self._version_range}]", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if Version(self.version) < "0.13" and is_msvc(self) and self.dependencies["imgui"].options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} doesn't support shared imgui.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["IMPLOT_SRC_DIR"] = self.source_folder.replace("\\", "/")
        if Version(self.version) < "0.16":
            # Set in code since v0.16 https://github.com/epezent/implot/commit/33c5a965f55f80057f197257d1d1cdb06523e963
            tc.preprocessor_definitions["IMGUI_DEFINE_MATH_OPERATORS"] = None
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        if Version(self.version) == "0.14" and Version(self.dependencies["imgui"].ref.version) >= "1.89.7":
            # https://github.com/ocornut/imgui/commit/51f564eea6333bae9242f40c983a3e29d119a9c2
            replace_in_file(self, os.path.join(self.source_folder, "implot.cpp"),
                            "ImGuiButtonFlags_AllowItemOverlap",
                            "ImGuiButtonFlags_AllowOverlap")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder="..")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "implot*.cpp", self.source_folder, os.path.join(self.package_folder, "share", "implot", "src"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["implot"]
        self.cpp_info.requires = ["imgui::core"]
        self.cpp_info.srcdirs = ["share/implot/src"]
