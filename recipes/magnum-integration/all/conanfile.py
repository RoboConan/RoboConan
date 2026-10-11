import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir

required_conan_version = ">=2.1"


class MagnumIntegrationConan(ConanFile):
    name = "magnum-integration"
    description = "Integration libraries for the Magnum C++11/C++14 graphics engine"
    license = "MIT"
    homepage = "https://magnum.graphics"
    topics = ("magnum", "graphics", "rendering", "3d", "2d", "opengl")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Integration libraries
        "with_bullet": [True, False],
        "with_dart": [True, False],
        "with_eigen": [True, False],
        "with_glm": [True, False],
        "with_imgui": [True, False],
        "with_ovr": [True, False],
        "with_yoga": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_bullet": True,
        "with_dart": False,
        "with_eigen": True,
        "with_glm": True,
        "with_imgui": True,
        "with_ovr": False,
        "with_yoga": False,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # https://github.com/mosra/magnum-integration/blob/e3d2b01b2067b514c04cb5d426da6941d0f09b1e/src/Magnum/BulletIntegration/Integration.h#L61-L62
        self.requires("magnum/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.with_bullet:
            # https://github.com/mosra/magnum-integration/blob/e3d2b01b2067b514c04cb5d426da6941d0f09b1e/src/Magnum/BulletIntegration/Integration.h#L35-L36
            self.requires("bullet3/[^3.25]", transitive_headers=True, transitive_libs=True)
        if self.options.with_eigen:
            # https://github.com/mosra/magnum-integration/blob/e3d2b01b2067b514c04cb5d426da6941d0f09b1e/src/Magnum/EigenIntegration/Integration.h#L82
            self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        if self.options.with_glm:
            # https://github.com/mosra/magnum-integration/blob/e3d2b01b2067b514c04cb5d426da6941d0f09b1e/src/Magnum/GlmIntegration/Integration.h#L67-L69
            self.requires("glm/[^1.0.1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_imgui:
            # https://github.com/mosra/magnum-integration/blob/e3d2b01b2067b514c04cb5d426da6941d0f09b1e/src/Magnum/ImGuiIntegration/Context.hpp#L41-L48
            self.requires("imgui/[^1.92.9b]", transitive_headers=True, transitive_libs=True)
        if self.options.with_yoga:
            # https://github.com/mosra/magnum-integration/blob/e3d2b01b2067b514c04cb5d426da6941d0f09b1e/src/Magnum/YogaIntegration/Layouter.h#L34-L36
            self.requires("yoga/[^3.2.0]", transitive_headers=True, transitive_libs=True)
            self.requires("magnum-extras/[*]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.options.shared != self.dependencies["magnum"].options.shared:
            raise ConanInvalidConfiguration(
                "The 'shared' option must match magnum:shared because upstream inherits "
                "MAGNUM_BUILD_STATIC from the Magnum package"
            )
        if self.options.with_dart:
            raise ConanInvalidConfiguration("DART does not have a RoboConan recipe")
        if self.options.with_ovr:
            raise ConanInvalidConfiguration("OVR does not have a RoboConan recipe")

        magnum = self.dependencies["magnum"].options

        def _require(option, reason):
            if not magnum.get_safe(option, False):
                raise ConanInvalidConfiguration(f"{reason} requires 'magnum:{option}=True'")

        if self.options.with_bullet:
            for option in ("gl", "scene_graph", "shaders"):
                _require(option, "BulletIntegration")
        if self.options.with_imgui:
            for option in ("gl", "shaders"):
                _require(option, "ImGuiIntegration")
        if self.options.with_yoga and not self.dependencies["magnum-extras"].options.ui:
            raise ConanInvalidConfiguration("YogaIntegration requires 'magnum-extras:ui=True'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["MAGNUM_BUILD_STATIC"] = not self.options.shared
        tc.cache_variables["MAGNUM_BUILD_STATIC_PIC"] = self.options.get_safe("fPIC", False)
        tc.cache_variables["MAGNUM_BUILD_TESTS"] = False
        tc.cache_variables["MAGNUM_BUILD_GL_TESTS"] = False
        if self.options.with_yoga:
            # https://github.com/mosra/magnum-integration/blob/e3d2b01b2067b514c04cb5d426da6941d0f09b1e/src/Magnum/YogaIntegration/CMakeLists.txt#L52-L73
            # Ensure Yoga's configuration-specific CMakeDeps usage requirements
            # are available to the upstream try_compile().
            tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        # These normally come from upstream's FindMagnum.cmake. CMakeDeps
        # finds Magnum's generated config first, which intentionally contains
        # target metadata only.
        tc.cache_variables["CMAKE_INSTALL_DATADIR"] = "share"
        tc.cache_variables["MAGNUM_BINARY_INSTALL_DIR"] = "bin"
        tc.cache_variables["MAGNUM_LIBRARY_INSTALL_DIR"] = "lib"
        tc.cache_variables["MAGNUM_INCLUDE_INSTALL_DIR"] = "include/Magnum"
        tc.cache_variables["MAGNUM_WITH_BULLETINTEGRATION"] = self.options.with_bullet
        tc.cache_variables["MAGNUM_WITH_DARTINTEGRATION"] = self.options.with_dart
        tc.cache_variables["MAGNUM_WITH_EIGENINTEGRATION"] = self.options.with_eigen
        tc.cache_variables["MAGNUM_WITH_GLMINTEGRATION"] = self.options.with_glm
        tc.cache_variables["MAGNUM_WITH_IMGUIINTEGRATION"] = self.options.with_imgui
        tc.cache_variables["MAGNUM_WITH_OVRINTEGRATION"] = self.options.with_ovr
        tc.cache_variables["MAGNUM_WITH_YOGAINTEGRATION"] = self.options.with_yoga
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.with_bullet:
            deps.set_property("bullet3", "cmake_file_name", "Bullet")
            deps.set_property("bullet3", "cmake_target_name", "Bullet::LinearMath")
        if self.options.with_glm:
            deps.set_property("glm", "cmake_file_name", "GLM")
            deps.set_property("glm", "cmake_target_name", "GLM::GLM")
        if self.options.with_imgui:
            deps.set_property("imgui", "cmake_file_name", "ImGui")
            deps.set_property("imgui::core", "cmake_target_name", "ImGui::ImGui")
        if self.options.with_yoga:
            deps.set_property("yoga", "cmake_file_name", "yoga")
            deps.set_property("yoga", "cmake_target_name", "yoga::yogacore")
        deps.generate()

    def _patch_sources(self):
        # RoboConan's imgui package provides a compiled ImGui::ImGui target, so
        # the upstream source-only target is neither present nor needed.
        replace_in_file(self, os.path.join(self.source_folder, "src", "Magnum", "ImGuiIntegration", "CMakeLists.txt"),
                        "        ImGui::Sources", "")

    def build(self):
        self._patch_sources()
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
        self.cpp_info.set_property("cmake_file_name", "MagnumIntegration")
        suffix = "-d" if self.settings.build_type == "Debug" else ""

        if self.options.with_bullet:
            bullet = self.cpp_info.components["bullet"]
            bullet.set_property("cmake_target_name", "MagnumIntegration::Bullet")
            bullet.libs = [f"MagnumBulletIntegration{suffix}"]
            bullet.requires = [
                "magnum::gl", "magnum::magnum_main", "magnum::scene_graph", "magnum::shaders",
                "bullet3::bullet3",
            ]
        if self.options.with_eigen:
            eigen = self.cpp_info.components["eigen"]
            eigen.set_property("cmake_target_name", "MagnumIntegration::Eigen")
            eigen.requires = ["magnum::magnum_main", "eigen::eigen"]
        if self.options.with_glm:
            glm = self.cpp_info.components["glm"]
            glm.set_property("cmake_target_name", "MagnumIntegration::Glm")
            glm.libs = [f"MagnumGlmIntegration{suffix}"]
            glm.requires = ["magnum::magnum_main", "glm::glm"]
        if self.options.with_imgui:
            imgui = self.cpp_info.components["imgui"]
            imgui.set_property("cmake_target_name", "MagnumIntegration::ImGui")
            imgui.libs = [f"MagnumImGuiIntegration{suffix}"]
            imgui.requires = ["magnum::gl", "magnum::shaders", "imgui::core"]
        if self.options.with_yoga:
            yoga = self.cpp_info.components["yoga"]
            yoga.set_property("cmake_target_name", "MagnumIntegration::Yoga")
            yoga.libs = [f"MagnumYogaIntegration{suffix}"]
            yoga.requires = ["magnum-extras::ui", "yoga::yoga"]
