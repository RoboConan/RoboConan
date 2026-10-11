import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class fastgltf(ConanFile):
    name = "fastgltf"
    description = "A modern C++17 glTF 2.0 library focused on speed, correctness, and usability"
    license = "MIT"
    homepage = "https://github.com/spnda/fastgltf"
    topics = ("gltf", "simd", "cpp17")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_small_vector": [True, False],
        "disable_custom_memory_pool": [True, False],
        "use_64bit_float": [True, False],
        "enable_khr_implicit_shapes": [True, False],
        "enable_khr_physics_rigid_bodies": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_small_vector": False,
        "disable_custom_memory_pool": False,
        "use_64bit_float": False,
        "enable_khr_implicit_shapes": False,
        "enable_khr_physics_rigid_bodies": False,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder='src')

    @property
    def _enable_khr_implicit_shapes(self):
        return (
            self.options.get_safe("enable_khr_implicit_shapes")
            or self.options.get_safe("enable_khr_physics_rigid_bodies")
        )

    @property
    def _config_definitions(self):
        definitions = {
            "FASTGLTF_USE_CUSTOM_SMALLVECTOR": self.options.get_safe("enable_small_vector"),
            "FASTGLTF_DISABLE_CUSTOM_MEMORY_POOL": self.options.get_safe("disable_custom_memory_pool"),
            "FASTGLTF_USE_64BIT_FLOAT": self.options.get_safe("use_64bit_float"),
            "FASTGLTF_ENABLE_KHR_PHYSICS_RIGID_BODIES": self.options.get_safe("enable_khr_physics_rigid_bodies"),
        }
        if self.options.get_safe("enable_khr_implicit_shapes") is not None:
            definitions["FASTGLTF_ENABLE_KHR_IMPLICIT_SHAPES"] = self._enable_khr_implicit_shapes
        return definitions

    def requirements(self):
        self.requires("simdjson/[>=3.11.5 <6]")

    def package_id(self):
        if self.info.options.get_safe("enable_khr_physics_rigid_bodies"):
            self.info.options.enable_khr_implicit_shapes = True

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        for variable, value in self._config_definitions.items():
            if value is not None:
                tc.variables[variable] = value
        tc.variables["FASTGLTF_ENABLE_INSTALL"] = True
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["fastgltf"]
        for define, value in self._config_definitions.items():
            if value is not None:
                self.cpp_info.defines.append(f"{define}={int(bool(value))}")

        if self.settings.os == "Android":
            self.cpp_info.system_libs.append("android")
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "9.1":
            self.cpp_info.system_libs.append("stdc++fs")
        elif self.settings.compiler == "clang" and Version(self.settings.compiler.version) < "9":
            self.cpp_info.system_libs.append("c++fs")
