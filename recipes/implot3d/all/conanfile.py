import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.28"


class Implot3dConan(ConanFile):
    name = "implot3d"
    description = "Immediate Mode 3D Plotting for Dear ImGui"
    license = "MIT"
    homepage = "https://github.com/brenocq/implot3d"
    topics = ("imgui", "plot", "3d", "graphics")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_demo": [True, False],
        "build_meshes": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_demo": True,
        "build_meshes": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def layout(self):
        cmake_layout(self, src_folder="src")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.build_demo:
            self.options.build_meshes.value = True

    def requirements(self):
        self.requires("imgui/[^1.91]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Use the CMake-generated import/export declarations for shared builds.
        replace_in_file(self, os.path.join(self.source_folder, "implot3d.h"),
                        '#include "imgui.h"',
                        '#include "imgui.h"\n#include "implot3d_export.h"')
        # The public mesh arrays need dllimport/dllexport annotations on Windows.
        header = os.path.join(self.source_folder, "implot3d.h")
        for declaration in (
            "ImPlot3DPoint cube_vtx[CUBE_VTX_COUNT]",
            "unsigned int cube_idx[CUBE_IDX_COUNT]",
            "ImPlot3DPoint sphere_vtx[SPHERE_VTX_COUNT]",
            "unsigned int sphere_idx[SPHERE_IDX_COUNT]",
            "ImPlot3DPoint duck_vtx[DUCK_VTX_COUNT]",
            "unsigned int duck_idx[DUCK_IDX_COUNT]",
        ):
            replace_in_file(self, header, f"extern {declaration};",
                            f"extern IMPLOT3D_API {declaration};")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["IMPLOT3D_BUILD_DEMO"] = self.options.build_demo
        tc.cache_variables["IMPLOT3D_BUILD_MESHES"] = self.options.build_meshes
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

    def package_info(self):
        self.cpp_info.libs = ["implot3d"]
        self.cpp_info.requires = ["imgui::core"]
