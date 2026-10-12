import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class DaqpConan(ConanFile):
    name = "daqp"
    description = "DAQP is a dual active-set solver for convex quadratic programming"
    license = "MIT"
    homepage = "https://github.com/darnstrom/daqp"
    topics = ("optimization", "quadratic-programming", "active-set", "solver")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "soft_weights": [True, False],
        "with_eigen": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "soft_weights": False,
        "with_eigen": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if Version(self.version) < "0.7":
            del self.options.with_eigen

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.get_safe("with_eigen"):
            self.languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("with_eigen"):
            self.requires("eigen/[>=3.4 <6]", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_POSITION_INDEPENDENT_CODE ON)", "")
        replace_in_file(self, "CMakeLists.txt", "target_link_libraries(daqpstat daqp)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["TEST"] = False
        tc.cache_variables["PROFILING"] = False
        tc.cache_variables["MATLAB"] = False
        tc.cache_variables["JULIA"] = False
        tc.cache_variables["EIGEN"] = self.options.get_safe("with_eigen")
        tc.cache_variables["SOFT_WEIGHTS"] = self.options.soft_weights
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        if self.options.shared:
            replace_in_file(self, cmakelists, "install(TARGETS daqpstat ", "message(TRACE ")
            save(self, cmakelists, "\nset_target_properties(daqpstat PROPERTIES EXCLUDE_FROM_ALL 1)\n", append=True)
        else:
            replace_in_file(self, cmakelists, "install(TARGETS daqp ", "message(TRACE ")
            save(self, cmakelists, "\nset_target_properties(daqp PROPERTIES EXCLUDE_FROM_ALL 1)\n", append=True)
        if self.options.get_safe("with_eigen"):
            eigen_cmakelists = os.path.join(self.source_folder, "interfaces", "daqp-eigen", "CMakeLists.txt")
            replace_in_file(self, eigen_cmakelists,
                            "add_library(${PROJECT_NAME} SHARED daqp.cpp)",
                            "add_library(${PROJECT_NAME} daqp.cpp)")
            replace_in_file(self, eigen_cmakelists,
                            "target_link_libraries(${PROJECT_NAME} PUBLIC Eigen3::Eigen daqpstat)",
                            f"target_link_libraries(${{PROJECT_NAME}} PUBLIC Eigen3::Eigen "
                            f"{'daqp' if self.options.shared else 'daqpstat'})")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "daqp")
        self.cpp_info.components["core"].set_property("cmake_target_name", "daqp")
        self.cpp_info.components["core"].set_property("cmake_target_aliases", ["daqpstat"])
        self.cpp_info.components["core"].libs = ["daqp" if self.options.shared else "daqpstat"]
        self.cpp_info.components["core"].includedirs = ["include"]
        if self.options.soft_weights:
            if Version(self.version) < "0.8":
                self.cpp_info.components["core"].defines.append("SOFT_WEIGHTS")
        elif Version(self.version) >= "0.8":
            self.cpp_info.components["core"].defines.append("DAQP_NO_SOFT_WEIGHTS")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["core"].system_libs = ["m"]

        if self.options.get_safe("with_eigen"):
            self.cpp_info.components["daqp_eigen"].set_property("cmake_target_name", "daqp_eigen")
            self.cpp_info.components["daqp_eigen"].libs = ["daqp_eigen"]
            self.cpp_info.components["daqp_eigen"].requires = ["core", "eigen::eigen"]
