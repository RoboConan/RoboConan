import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SFML_WITH_WINDOW"] = self.dependencies["sfml"].options.window
        tc.variables["SFML_WITH_GRAPHICS"] = self.dependencies["sfml"].options.graphics
        tc.variables["SFML_WITH_NETWORK"] = self.dependencies["sfml"].options.network
        tc.variables["SFML_WITH_AUDIO"] = self.dependencies["sfml"].options.audio
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            components = ["system"]
            for component in ["window", "graphics", "network", "audio"]:
                if self.dependencies["sfml"].options.get_safe(component, False):
                    components.append(component)
            for component in components:
                bin_path = os.path.join(self.cpp.build.bindir, f"test_{component}")
                self.run(bin_path, env="conanrun")
