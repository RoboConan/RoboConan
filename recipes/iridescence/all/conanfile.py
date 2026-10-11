import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class IridescenceConan(ConanFile):
    name = "iridescence"
    description = "3D visualization library for rapid prototyping of 3D algorithms"
    license = "MIT"
    homepage = "https://koide3.github.io/iridescence"
    topics = ("visualization", "imgui", "opengl", "localization", "mapping", "point-cloud", "slam")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "imgui/*:docking": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("assimp/[^5.1.6]")
        self.requires("boost/[^1.71.0]", transitive_headers=True, libs=False)
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        self.requires("glm/[^1.0.1]")
        self.requires("libjpeg-meta/latest")
        self.requires("libpng/[~1.6]")
        self.requires("portable-file-dialogs/0.1.0+git.20221111", transitive_headers=True)
        self.requires("imgui/[^1.90]", transitive_headers=True, transitive_libs=True)
        self.requires("implot/[<2]", transitive_headers=True, transitive_libs=True)
        self.requires("imguizmo/[^1.9]", transitive_headers=True, transitive_libs=True)
        self.requires("glfw/[^3.4]", transitive_headers=True, transitive_libs=True)
        self.requires("opengl/system", transitive_libs=True)
        if Version(self.version) >= "1.0.0":
            self.requires("rapidhash/[^3.1-git.20260819, include_prerelease]")
        # https://github.com/koide3/iridescence/blob/7034275ee6516eb4d155f645cd8327173edfeb9d/thirdparty/gl3w/GL/glcorearb.h#L82
        self.requires("khrplatform/0.0+git.20200529", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, 17)

    def package_id(self):
        # Iridescence compiles ImGui backend sources against the selected headers,
        # and its docking compatibility definition also depends on ImGui options.
        self.info.requires["imgui"].full_package_mode()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["IMGUI_BACKENDS"] = os.path.join(self.dependencies["imgui"].package_folder, "share", "imgui", "bindings").replace("\\", "/")
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_PYTHON_BINDINGS"] = False
        tc.variables["BUILD_WITH_MARCH_NATIVE"] = False
        tc.variables["BUILD_EXT_TESTS"] = False
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        if not self.dependencies["imgui"].options.docking:
            tc.preprocessor_definitions["ImGuiConfigFlags_DockingEnable"] = "0"
        if self.settings.os == "Windows":
            # TODO: submit a patch upstream
            tc.preprocessor_definitions["_USE_MATH_DEFINES"] = None
            tc.preprocessor_definitions["NOMINMAX"] = None
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
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Iridescence")
        self.cpp_info.set_property("cmake_target_name", "Iridescence::Iridescence")

        self.cpp_info.libs = ["iridescence"]
        self.cpp_info.includedirs.append("include/iridescence")
        self.cpp_info.resdirs = ["share/iridescence/data"]

        self.cpp_info.requires = [
            "assimp::assimp",
            "boost::headers",
            "eigen::eigen",
            "glfw::glfw",
            "glm::glm",
            "imgui::core",
            "imguizmo::imguizmo",
            "implot::implot",
            "khrplatform::khrplatform",
            "libjpeg-meta::jpeg",
            "libpng::libpng",
            "opengl::opengl",
            "portable-file-dialogs::portable-file-dialogs",
        ]
        if Version(self.version) >= "1.0.0":
            self.cpp_info.requires.append("rapidhash::rapidhash")

        if not self.options.shared and self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "pthread", "dl"])
