import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class XtensorConan(ConanFile):
    name = "xtensor"
    package_type = "header-library"
    description = "C++ tensors with broadcasting and lazy computing"
    license = "BSD-3-Clause"
    homepage = "https://github.com/xtensor-stack/xtensor"
    topics = ("numpy", "multidimensional-arrays", "tensors")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "xsimd": [True, False],
        "tbb": [True, False],
        "openmp": [True, False],
    }
    default_options = {
        "xsimd": True,
        "tbb": False,
        "openmp": True,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("xtl/[>=0.7.5 <1]")
        self.requires("nlohmann_json/[^3]")
        if self.options.xsimd:
            if Version(self.version) >= "0.24.0":
                self.requires("xsimd/[^13.0.0]")
            else:
                self.requires("xsimd/[^7.5.0]")
        if self.options.tbb:
            self.requires("onetbb/[>=2021]")
        if self.options.openmp:
            self.requires("openmp/system")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.29]")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.options.tbb and self.options.openmp:
            raise ConanInvalidConfiguration(
                "The options 'tbb' and 'openmp' cannot be used together."
            )

        check_min_cppstd(self, 14 if Version(self.version) < "0.26.0" else 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if Version(self.version) < "0.26.0":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"  # CMake 4 support
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "xtensor")
        self.cpp_info.set_property("cmake_target_name", "xtensor")
        self.cpp_info.set_property("pkg_config_name", "xtensor")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.options.xsimd:
            self.cpp_info.defines.append("XTENSOR_USE_XSIMD")
        if self.options.tbb:
            self.cpp_info.defines.append("XTENSOR_USE_TBB")
        if self.options.openmp:
            self.cpp_info.defines.append("XTENSOR_USE_OPENMP")
