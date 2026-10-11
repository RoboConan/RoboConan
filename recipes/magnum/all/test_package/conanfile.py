import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain, CMakeDeps


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    @property
    def _executables(self):
        available = []
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
        for executable, opt_name in all_execs:
            if self.dependencies["magnum"].options.get_safe(opt_name, False):
                available.append(executable)
        return available

    def generate(self):
        tc = CMakeToolchain(self)
        for exec in self._executables:
            tc.variables["EXEC_{}".format(exec.replace("-", "_")).upper()] = True
        for component, option in (
            ("MATERIAL_TOOLS", "material_tools"),
            ("SCENE_TOOLS", "scene_tools"),
            ("SHADER_TOOLS", "shader_tools"),
        ):
            tc.variables[f"WITH_{component}"] = self.dependencies["magnum"].options.get_safe(option, False)
        tc.variables["TARGET_GL"] = bool(self.dependencies["magnum"].options.target_gl)
        plugins_root = self.dependencies["magnum"].conf_info.get("user.magnum:plugins_basepath", check_type=str)
        tc.variables["IMPORTER_PLUGINS_FOLDER"] = os.path.join(plugins_root, "importers").replace("\\", "/")
        tc.variables["OBJ_FILE"] = os.path.join(self.source_folder, "triangleMesh.obj").replace("\\", "/")
        tc.variables["SHARED_PLUGINS"] = self.dependencies["magnum"].options.shared_plugins
        tc.generate()
        deps = CMakeDeps(self)
        if "egl" in self.dependencies.host:
            # Match Magnum's installed FindEGL.cmake contract, as done by the
            # Qt recipe for the same egl/system dependency.
            deps.set_property("egl", "cmake_file_name", "EGL")
            deps.set_property("egl", "cmake_find_mode", "module")
            deps.set_property("egl", "cmake_target_name", "EGL::EGL")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            for exec in self._executables:
                self.run(f"magnum-{exec} --help", env="conanrun")

            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
