import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime

required_conan_version = ">=2.1"


class ShadercConan(ConanFile):
    name = "shaderc"
    description = "A collection of tools, libraries and tests for shader compilation."
    license = "Apache-2.0"
    homepage = "https://github.com/google/shaderc"
    topics = ("glsl", "hlsl", "msl", "spirv", "spir-v", "glslc")

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

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _spirv_version(self):
        return self.conan_data.get("siprv_mapping")[self.version]

    def requirements(self):
        # transitive_headers=True is not required for any of the dependencies
        self.requires(f"glslang/{self._spirv_version}")
        self.requires(f"spirv-tools/{self._spirv_version}")
        self.requires(f"spirv-headers/{self._spirv_version}")

    def validate(self):
        check_min_cppstd(self, 11)

    def validate_build(self):
        check_min_cppstd(self, 17)

    def package_id(self):
        self.info.requires["glslang"].full_package_mode()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.17.2 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        venv = VirtualBuildEnv(self)
        venv.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["SHADERC_SKIP_INSTALL"] = False
        tc.cache_variables["SHADERC_SKIP_EXAMPLES"] = True
        tc.cache_variables["SHADERC_SKIP_TESTS"] = True
        tc.cache_variables["ENABLE_CODE_COVERAGE"] = False
        tc.cache_variables["SHADERC_ENABLE_WERROR_COMPILE"] = False
        tc.cache_variables["SHADERC_ENABLE_HLSL"] = self.dependencies["glslang"].options.hlsl
        if is_msvc(self):
            tc.cache_variables["SHADERC_ENABLE_SHARED_CRT"] = not is_msvc_static_runtime(self)
        tc.generate()

        self.dependencies["glslang"].cpp_info.components["glslang-core"].includedirs.append(
            os.path.join(self.dependencies["glslang"].package_folder, "include", "glslang")
        )

        deps = CMakeDeps(self)
        deps.set_property("glslang::glslang-core", "cmake_target_name", "glslang")
        deps.set_property("glslang::oglcompiler", "cmake_target_name", "OGLCompiler")
        deps.set_property("glslang::hlsl", "cmake_target_name", "HLSL")
        deps.set_property("glslang::spirv", "cmake_target_name", "SPIRV")
        deps.set_property("glslang::osdependent", "cmake_target_name", "OSDependent")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        fix_apple_shared_install_name(self)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        if self.options.shared:
            for library in ["shaderc", "shaderc_util", "shaderc_combined"]:
                rm(self, f"*{library}.a", os.path.join(self.package_folder, "lib"))
                rm(self, f"*{library}.lib", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*shaderc_shared*", os.path.join(self.package_folder, "lib"))
            rm(self, "*shaderc_shared*", os.path.join(self.package_folder, "bin"))
            rm(self, "*shaderc_combined*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.set_property("pkg_config_name", "shaderc")
            self.cpp_info.libs = ["shaderc_shared"]
            self.cpp_info.defines.append("SHADERC_SHAREDLIB")
        else:
            self.cpp_info.set_property("pkg_config_name", "shaderc_static")
            self.cpp_info.libs = ["shaderc", "shaderc_util"]
            if stdcpp_library(self):
                self.cpp_info.system_libs.append(stdcpp_library(self))

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("pthread")

        self.cpp_info.requires = [
            "glslang::spirv",
            "spirv-tools::spirv-tools-core",
            "spirv-headers::spirv-headers",
        ]
