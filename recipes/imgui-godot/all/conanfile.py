import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version
from conan.tools.system import PyEnv

required_conan_version = ">=2.25"


class ImguiGodotConan(ConanFile):
    name = "imgui-godot"
    description = "Dear ImGui native GDExtension backend for Godot 4"
    license = "MIT"
    homepage = "https://github.com/pkdawson/imgui-godot"
    topics = ("godot", "imgui", "gdextension", "gui")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "gdscript_bindings": [True, False],
    }
    default_options = {
        "gdscript_bindings": False,
        "imgui/*:docking": True,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        copy(self, "gdscript_stubs.cpp", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("imgui/[^1.91.6 <1.93]", transitive_headers=True, transitive_libs=True)
        self.requires("godot-cpp/[^10]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 20)
        if self.settings.os not in ["Linux", "Macos", "Windows"]:
            raise ConanInvalidConfiguration(f"imgui-godot does not support {self.settings.os}")
        if self.settings.arch not in ["x86_64", "armv8"]:
            raise ConanInvalidConfiguration("imgui-godot requires a x86_64 or armv8")
        if self.settings.os == "Windows" and self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration("imgui-godot only supports x86_64 on Windows")

        imgui_opts = self.dependencies["imgui"].options
        if not imgui_opts.docking:
            raise ConanInvalidConfiguration("imgui-godot requires imgui:docking=True")
        if imgui_opts.use_wchar32:
            raise ConanInvalidConfiguration("imgui-godot requires imgui:use_wchar32=False")
        if self.options.gdscript_bindings and not imgui_opts.enable_demo_windows:
            raise ConanInvalidConfiguration("imgui-godot:gdscript_bindings=True requires imgui:enable_demo_windows=True")

        api_version = Version(self.dependencies["godot-cpp"].options.api_version)
        min_api = "4.3" if self.version == "6.3.2" else "4.5"
        max_api = "4.8"
        if not (min_api <= api_version < max_api):
            raise ConanInvalidConfiguration(f"{self.ref} supports Godot API versions >={min_api} <{max_api}")

    def package_id(self):
        self.info.requires["imgui"].full_package_mode()
        self.info.requires["godot-cpp"].full_package_mode()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        get(self, **self.conan_data["dear_bindings"][self.version], destination="gdext/dear_bindings", strip_root=True)
        apply_conandata_patches(self)

    @property
    def _platform(self):
        return str(self.settings.os).lower()

    @property
    def _config(self):
        target = str(self.dependencies["godot-cpp"].options.target)
        return "release" if target == "template_release" else "debug"

    @property
    def _arch(self):
        return "arm64" if self.settings.arch == "armv8" else "x86_64"

    @property
    def _lib(self):
        name = f"imgui-godot-native.{self._platform}.{self._config}"
        if self.settings.os != "Macos":
            name += f".{self._arch}"
        if self.settings.os == "Windows":
            name = f"lib{name}"
        return name

    @property
    def _lib_file(self):
        match str(self.settings.os):
            case "Windows":
                return f"{self._lib}.dll"
            case "Linux":
                return f"lib{self._lib}.so"
            case "Macos":
                return f"lib{self._lib}.dylib"
        raise ConanException("Unexpected self.settings.os")

    @property
    def _addon_rel_path(self):
        return "share/imgui-godot/addons/imgui-godot"

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["IMGUI_GODOT_GDSCRIPT_BINDINGS"] = self.options.gdscript_bindings
        tc.cache_variables["IMGUI_GODOT_LIBRARY_NAME"] = self._lib
        tc.cache_variables["IMGUI_GODOT_ADDON_DIR"] = self._addon_rel_path.replace("\\", "/")
        if self.options.gdscript_bindings:
            tc.cache_variables["IMGUI_GODOT_BINDINGS_DIR"] = os.path.join(self.build_folder, "bindings", "gen").replace("\\", "/")
        tc.generate()
        CMakeDeps(self).generate()
        if self.options.gdscript_bindings:
            python_env = PyEnv(self)
            python_env.install(["ply==3.11"])
            python_env.generate()


    def build(self):
        if self.options.gdscript_bindings:
            binding_dir = os.path.join(self.build_folder, "bindings")
            copy(self, "*", os.path.join(self.source_folder, "gdext", "dear_bindings"), os.path.join(binding_dir, "dear_bindings"))
            copy(self, "gds_bindings.py", os.path.join(self.source_folder, "gdext", "scripts"), binding_dir)
            imgui_include = self.dependencies["imgui"].cpp_info.components["core"].includedirs[0]
            copy(self, "imgui.h", imgui_include, os.path.join(binding_dir, "imgui"))
            copy(self, "imconfig.h", imgui_include, os.path.join(binding_dir, "imgui"))
            self.run("python gds_bindings.py", cwd=binding_dir, env="conanbuild")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        addon_dir = os.path.join(self.package_folder, self._addon_rel_path)
        compatibility = self.dependencies["godot-cpp"].options.api_version
        save(self, os.path.join(addon_dir, "imgui-godot-native.gdextension"), textwrap.dedent(f'''\
            [configuration]
            entry_symbol = "ign_init"
            compatibility_minimum = {compatibility}

            [libraries]
            {self._platform}.{self._config}.{self._arch} = "bin/{self._lib_file}"
        '''))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "imgui-godot")
        self.cpp_info.set_property("cmake_target_name", "imgui-godot::imgui-godot")
        # No .lib: Godot loads the GDExtension at runtime; consumers must not link it directly.
        self.cpp_info.resdirs = ["share/imgui-godot"]
        self.cpp_info.defines = ['IMGUI_USER_CONFIG="imgui-godot/imconfig-godot.h"']
        self.cpp_info.requires = ["godot-cpp::godot-cpp", "imgui::core"]
