import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SpirvtoolsConan(ConanFile):
    name = "spirv-tools"
    homepage = "https://github.com/KhronosGroup/SPIRV-Tools/"
    description = "Create and optimize SPIRV shaders"
    topics = ("spirv", "spirv-v", "vulkan", "opengl", "opencl", "hlsl", "khronos")
    license = "Apache-2.0"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_executables": [True, False],
        "with_mimalloc": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_executables": True,
        "with_mimalloc": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if Version(self.version) < "1.4.363.0":
            self.options.rm_safe("with_mimalloc")

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _shared_auxiliary_libraries(self):
        return Version(self.version) >= "1.2.198.0"

    @property
    def _has_diff(self):
        return Version(self.version) >= "1.3.211.0"

    def requirements(self):
        self.requires(f"spirv-headers/{self.version}")
        if self.options.get_safe("with_mimalloc"):
            self.requires("mimalloc/[>=2.2.4 <4]")

    def package_id(self):
        self.info.requires["spirv-headers"].full_package_mode()

    def validate_build(self):
        # newer versions of the library require C++17 for internals
        check_min_cppstd(self, 11 if Version(self.version) < "1.3.243" else 17)

    def validate(self):
        # The interface requires C++11
        check_min_cppstd(self, 11)
        if (self.options.get_safe("with_mimalloc")
                and self.settings.os != "Windows"
                and self.dependencies["mimalloc"].options.override):
            raise ConanInvalidConfiguration("mimalloc override mode is not supported")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.17.2 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_POSITION_INDEPENDENT_CODE ON)", "")
        replace_in_file(self, "CMakeLists.txt", "add_subdirectory(external)",
                        "add_subdirectory(external)\nfind_package(SPIRV-Headers REQUIRED CONFIG)")
        spirv_headers_link = "target_link_libraries(${target} PUBLIC SPIRV-Headers::SPIRV-Headers)"
        if Version(self.version) < "1.4.321.0":
            spirv_headers_link = "target_link_libraries(${target} SPIRV-Headers::SPIRV-Headers)"
        replace_in_file(self, os.path.join(self.source_folder, "source", "CMakeLists.txt"),
                        "  spvtools_default_compile_options(${target})",
                        "  spvtools_default_compile_options(${target})\n"
                        f"  {spirv_headers_link}")

    def generate(self):
        tc = CMakeToolchain(self)
        # SPIRV-Tools always builds its hidden-visibility shared core. Disabling
        # the static build makes the full-visibility core and the other SPIR-V
        # Tools libraries follow BUILD_SHARED_LIBS.
        if self._shared_auxiliary_libraries:
            tc.variables["SPIRV_TOOLS_BUILD_STATIC"] = not self.options.shared
        # Required by the project's CMakeLists.txt
        tc.variables["SPIRV-Headers_SOURCE_DIR"] = self.dependencies["spirv-headers"].package_folder.replace("\\", "/")
        tc.variables["SPIRV_WERROR"] = False
        tc.variables["SKIP_SPIRV_TOOLS_INSTALL"] = False
        tc.variables["SPIRV_LOG_DEBUG"] = False
        tc.variables["SPIRV_SKIP_TESTS"] = True
        tc.variables["SPIRV_CHECK_CONTEXT"] = False
        tc.variables["SPIRV_BUILD_FUZZER"] = False
        tc.variables["SPIRV_SKIP_EXECUTABLES"] = not self.options.build_executables
        if self.options.get_safe("with_mimalloc"):
            tc.variables["MIMALLOC_DIR"] = self.dependencies["mimalloc"].package_folder.replace("\\", "/")
            tc.variables["SPIRV_TOOLS_USE_MIMALLOC"] = True
            tc.variables["SPIRV_TOOLS_USE_MIMALLOC_IN_STATIC_BUILD"] = not self.options.shared
        # For iOS/tvOS/watchOS
        tc.variables["CMAKE_MACOSX_BUNDLE"] = False
        tc.generate()
        deps = CMakeDeps(self)
        if self.options.get_safe("with_mimalloc"):
            deps.set_property("mimalloc", "cmake_target_name", "mimalloc::mimalloc")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _extract_version(self):
        # Based on https://github.com/KhronosGroup/SPIRV-Tools/blob/vulkan-sdk-1.4.313/cmake/write_pkg_config.cmake
        content = load(self, os.path.join(self.source_folder, "CHANGES"))
        return re.search(r"v(\d+(?:\.\d+)?) \d+-\d+-\d+", content).group(1)

    @property
    def _version_file(self):
        return os.path.join(self.package_folder, "share", "conan", self.name, "VERSION")

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        save(self, self._version_file, self._extract_version())
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        if self.options.shared and self._shared_auxiliary_libraries:
            for library in [
                "SPIRV-Tools", "SPIRV-Tools-opt", "SPIRV-Tools-link",
                "SPIRV-Tools-reduce", "SPIRV-Tools-lint", "SPIRV-Tools-diff",
            ]:
                rm(self, f"*{library}.a", os.path.join(self.package_folder, "lib"))
                rm(self, f"*{library}.lib", os.path.join(self.package_folder, "lib"))
        elif not self.options.shared:
            rm(self, "*SPIRV-Tools-shared*", os.path.join(self.package_folder, "lib"))
            rm(self, "*SPIRV-Tools-shared*", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SPIRV-Tools")
        self.cpp_info.set_property("pkg_config_name", "SPIRV-Tools-shared" if self.options.shared else "SPIRV-Tools")
        self.cpp_info.set_property("system_package_version", load(self, self._version_file).strip())

        # SPIRV-Tools
        self.cpp_info.components["spirv-tools-core"].set_property(
            "cmake_target_name", "SPIRV-Tools-shared" if self.options.shared else "SPIRV-Tools-static"
        )
        self.cpp_info.components["spirv-tools-core"].set_property(
            "cmake_target_aliases",
            ["SPIRV-Tools", "SPIRV-Tools-static" if self.options.shared else "SPIRV-Tools-shared"],
        )
        self.cpp_info.components["spirv-tools-core"].libs = [
            "SPIRV-Tools-shared" if self.options.shared else "SPIRV-Tools"
        ]
        self.cpp_info.components["spirv-tools-core"].requires = ["spirv-headers::spirv-headers"]
        if self.options.get_safe("with_mimalloc"):
            self.cpp_info.components["spirv-tools-core"].requires.append("mimalloc::mimalloc")
        if self.options.shared:
            self.cpp_info.components["spirv-tools-core"].defines = ["SPIRV_TOOLS_SHAREDLIB"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["spirv-tools-core"].system_libs.extend(["m", "rt"])
        if not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.components["spirv-tools-core"].system_libs.append(libcxx)

        full_visibility_core = "spirv-tools-core"
        if self.options.shared:
            full_visibility_core = "spirv-tools-full-visibility"
            component = self.cpp_info.components[full_visibility_core]
            component.set_property("cmake_target_name", "SPIRV-Tools-full-visibility")
            component.libs = ["SPIRV-Tools"]
            component.requires = ["spirv-headers::spirv-headers"]
            if self.options.get_safe("with_mimalloc"):
                component.requires.append("mimalloc::mimalloc")
            if self.settings.os in ["Linux", "FreeBSD"]:
                component.system_libs.extend(["m", "rt"])

        # SPIRV-Tools-opt
        self.cpp_info.components["spirv-tools-opt"].set_property("cmake_target_name", "SPIRV-Tools-opt")
        self.cpp_info.components["spirv-tools-opt"].libs = ["SPIRV-Tools-opt"]
        self.cpp_info.components["spirv-tools-opt"].requires = [full_visibility_core]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["spirv-tools-opt"].system_libs.append("m")

        # SPIRV-Tools-link
        self.cpp_info.components["spirv-tools-link"].set_property("cmake_target_name", "SPIRV-Tools-link")
        self.cpp_info.components["spirv-tools-link"].libs = ["SPIRV-Tools-link"]
        self.cpp_info.components["spirv-tools-link"].requires = ["spirv-tools-opt"]

        # SPIRV-Tools-reduce
        self.cpp_info.components["spirv-tools-reduce"].set_property("cmake_target_name", "SPIRV-Tools-reduce")
        self.cpp_info.components["spirv-tools-reduce"].libs = ["SPIRV-Tools-reduce"]
        self.cpp_info.components["spirv-tools-reduce"].requires = [full_visibility_core, "spirv-tools-opt"]

        # SPIRV-Tools-lint
        self.cpp_info.components["spirv-tools-lint"].set_property("cmake_target_name", "SPIRV-Tools-lint")
        self.cpp_info.components["spirv-tools-lint"].libs = ["SPIRV-Tools-lint"]
        self.cpp_info.components["spirv-tools-lint"].requires = [full_visibility_core, "spirv-tools-opt"]

        if self._has_diff:
            # SPIRV-Tools-diff
            self.cpp_info.components["spirv-tools-diff"].set_property("cmake_target_name", "SPIRV-Tools-diff")
            self.cpp_info.components["spirv-tools-diff"].libs = ["SPIRV-Tools-diff"]
            self.cpp_info.components["spirv-tools-diff"].requires = [full_visibility_core, "spirv-tools-opt"]
