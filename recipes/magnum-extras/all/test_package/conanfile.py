from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeConfigDeps, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeToolchain(self).generate()

        deps = CMakeConfigDeps(self)
        # The gcc15 profile replaces opengl/system with libglvnd. Preserve the
        # target name used by Magnum's published component metadata.
        if "libglvnd" in self.dependencies.host:
            deps.set_property("libglvnd::opengl", "cmake_target_aliases", ["opengl::opengl"])
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            "TEST_PLAYER": self.dependencies["magnum-extras"].options.get_safe("player", False),
            "TEST_UI": self.dependencies["magnum-extras"].options.ui,
            "TEST_UI_GALLERY": self.dependencies["magnum-extras"].options.get_safe("ui_gallery", False),
        })
        if self.dependencies["magnum-extras"].options.ui:
            cmake.build()

    def test(self):
        if can_run(self) and self.dependencies["magnum-extras"].options.ui:
            self.run(self.cpp.build.bindir + "/test_package", env="conanrun")
