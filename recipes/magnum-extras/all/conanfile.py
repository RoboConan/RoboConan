import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir

required_conan_version = ">=2.32"


class MagnumExtrasConan(ConanFile):
    name = "magnum-extras"
    description = "Extras for the Magnum C++11/C++14 graphics engine"
    license = "MIT"
    homepage = "https://magnum.graphics"
    topics = ("magnum", "graphics", "rendering", "3d", "2d", "opengl")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Applications
        "player": [True, False],
        "ui_gallery": [True, False],
        # Libraries
        "ui": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "player": True,
        "ui_gallery": True,
        "ui": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def config_options(self):
        if self.settings.os == "Android":
            self.options.rm_safe("player")
            self.options.rm_safe("ui_gallery")

    def configure(self):
        if self.options.get_safe("player", False) or self.options.get_safe("ui_gallery", False):
            self.options.ui.value = True

    def requirements(self):
        # https://github.com/mosra/magnum-extras/blob/79fff8c401a577f4bb68de730929e2a9b556d251/src/Magnum/Ui/AbstractTheme.h#L34-L37
        self.requires("magnum/[*]", transitive_headers=True, transitive_libs=True)
        if self.settings.os == "Emscripten" and (
            self.options.get_safe("player", False) or self.options.get_safe("ui_gallery", False)
        ):
            self.requires("magnum-plugins/[*]")

    def build_requirements(self):
        self.tool_requires("corrade/<host_version>")

    def validate(self):
        magnum = self.dependencies["magnum"].options
        if self.options.shared != magnum.shared:
            raise ConanInvalidConfiguration(
                "The 'shared' option must match magnum:shared because upstream inherits "
                "MAGNUM_BUILD_STATIC from the Magnum package"
            )

        def _require(option, reason):
            if not magnum.get_safe(option, False):
                raise ConanInvalidConfiguration(f"{reason} requires 'magnum:{option}=True'")

        if self.options.ui or self.options.get_safe("player", False) or self.options.get_safe("ui_gallery", False):
            _require("text", "Magnum Ui")
        if self.options.get_safe("player", False):
            for option in ("debug_tools", "gl", "mesh_tools", "primitives", "scene_graph", "shaders", "trade"):
                _require(option, "magnum-player")
        if self.options.get_safe("ui_gallery", False):
            _require("debug_tools", "magnum-ui-gallery")
        if self.options.get_safe("player", False) or self.options.get_safe("ui_gallery", False):
            application = "emscripten_application" if self.settings.os == "Emscripten" else "sdl2_application"
            _require(application, "Magnum Extras applications")

        if self.settings.os == "Emscripten" and "magnum-plugins" in self.dependencies.host:
            plugins = self.dependencies["magnum-plugins"].options
            if self.options.get_safe("player", False):
                for option in ("gltf_importer", "stb_imageimporter", "stbtruetype_font"):
                    if not plugins.get_safe(option, False):
                        raise ConanInvalidConfiguration(f"magnum-player requires 'magnum-plugins:{option}=True'")
            elif self.options.get_safe("ui_gallery", False) and not plugins.get_safe("stbtruetype_font", False):
                raise ConanInvalidConfiguration("magnum-ui-gallery requires 'magnum-plugins:stbtruetype_font=True'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["MAGNUM_BUILD_STATIC"] = not self.options.shared
        tc.cache_variables["MAGNUM_BUILD_STATIC_PIC"] = self.options.get_safe("fPIC", False)
        tc.cache_variables["MAGNUM_BUILD_TESTS"] = False
        tc.cache_variables["MAGNUM_BUILD_GL_TESTS"] = False
        # These normally come from upstream's FindMagnum.cmake. CMakeDeps
        # finds Magnum's generated config first, which intentionally contains
        # target metadata only.
        tc.cache_variables["CMAKE_INSTALL_DATADIR"] = "share"
        tc.cache_variables["MAGNUM_BINARY_INSTALL_DIR"] = "bin"
        tc.cache_variables["MAGNUM_LIBRARY_INSTALL_DIR"] = "lib"
        tc.cache_variables["MAGNUM_INCLUDE_INSTALL_DIR"] = "include/Magnum"
        tc.cache_variables["MAGNUM_WITH_PLAYER"] = self.options.get_safe("player", False)
        tc.cache_variables["MAGNUM_WITH_UI"] = self.options.ui
        tc.cache_variables["MAGNUM_WITH_UI_GALLERY"] = self.options.get_safe("ui_gallery", False)
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.get_safe("player", False) or self.options.get_safe("ui_gallery", False):
            application = "emscripten_application" if self.settings.os == "Emscripten" else "sdl2_application"
            deps.set_property(f"magnum::{application}", "cmake_target_aliases", ["Magnum::Application"])
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "MagnumExtras")

        executable_suffix = ".exe" if self.settings.os == "Windows" else ""
        if self.options.get_safe("player", False):
            player = self.cpp_info.components["player"]
            player.set_property("cmake_target_name", "MagnumExtras::player")
            player.exe = True
            player.location = f"bin/magnum-player{executable_suffix}"
        if self.options.get_safe("ui_gallery", False):
            ui_gallery = self.cpp_info.components["ui-gallery"]
            ui_gallery.set_property("cmake_target_name", "MagnumExtras::ui-gallery")
            ui_gallery.exe = True
            ui_gallery.location = f"bin/magnum-ui-gallery{executable_suffix}"

        if self.options.ui:
            suffix = "-d" if self.settings.build_type == "Debug" else ""
            ui = self.cpp_info.components["ui"]
            ui.set_property("cmake_target_name", "MagnumExtras::Ui")
            ui.libs = [f"MagnumUi{suffix}"]
            ui.requires = ["magnum::magnum_main", "magnum::text"]
            if self.dependencies["magnum"].options.target_gl:
                ui.requires.append("magnum::gl")
