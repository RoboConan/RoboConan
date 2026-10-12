import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime

required_conan_version = ">=2.1"


class AmplAslConan(ConanFile):
    name = "ampl-asl"
    description = "AMPL Solver Library - C library interface between AMPL modeling language and optimization solvers"
    license = "BSD-3-Clause AND SMLNJ"
    homepage = "https://github.com/ampl/asl"
    topics = ("optimization", "ampl", "solver", "linear-programming", "mixed-integer-programming", "nonlinear-optimization")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cxx": [True, False],
        "prefixless_includes": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cxx": False,
        "prefixless_includes": True,
        "with_openmp": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os == "Windows":
            self.options.shared.value = False
            self.package_type = "static-library"
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.cxx:
            self.languages = ["C"]

    def package_id(self):
        del self.info.options.prefixless_includes

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["BUILD_DYNRT_LIBS"] = not is_msvc_static_runtime(self)
        tc.cache_variables["BUILD_ASL_EXAMPLES"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_MT_LIBS"] = self.options.with_openmp
        tc.cache_variables["BUILD_CPP"] = self.options.cxx
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ampl-asl")

        # ASL version 1 component
        self.cpp_info.components["asl"].set_property("cmake_target_name", "asl")
        self.cpp_info.components["asl"].libs = ["asl"]
        if self.options.prefixless_includes:
            self.cpp_info.components["asl"].includedirs.append("include/asl")
        if self.settings.arch != "x86":
            self.cpp_info.components["asl"].defines.append("No_Control87")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["asl"].system_libs = ["m", "dl"]

        # ASL version 2 component
        self.cpp_info.components["asl2"].set_property("cmake_target_name", "asl2")
        self.cpp_info.components["asl2"].libs = ["asl2"]
        if self.options.prefixless_includes:
            self.cpp_info.components["asl2"].includedirs.append("include/asl2")
        if self.settings.arch != "x86":
            self.cpp_info.components["asl2"].defines.append("No_Control87")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["asl2"].system_libs = ["m", "dl"]

        if self.options.with_openmp:
            self.cpp_info.components["asl-mt"].set_property("cmake_target_name", "asl-mt")
            self.cpp_info.components["asl-mt"].libs = ["asl-mt"]
            if self.options.prefixless_includes:
                self.cpp_info.components["asl-mt"].includedirs.append("include/asl")
            self.cpp_info.components["asl-mt"].requires = ["openmp::openmp"]
            self.cpp_info.components["asl-mt"].defines.append("ALLOW_OPENMP")
            if self.settings.arch != "x86":
                self.cpp_info.components["asl-mt"].defines.append("No_Control87")

            self.cpp_info.components["asl2-mt"].set_property("cmake_target_name", "asl2-mt")
            self.cpp_info.components["asl2-mt"].libs = ["asl2-mt"]
            if self.options.prefixless_includes:
                self.cpp_info.components["asl2-mt"].includedirs.append("include/asl2")
            self.cpp_info.components["asl2-mt"].requires = ["openmp::openmp"]
            self.cpp_info.components["asl2-mt"].defines.append("ALLOW_OPENMP")
            if self.settings.arch != "x86":
                self.cpp_info.components["asl2-mt"].defines.append("No_Control87")

        if self.options.cxx:
            self.cpp_info.components["aslcpp"].set_property("cmake_target_name", "aslcpp")
            self.cpp_info.components["aslcpp"].libs = ["aslcpp"]
            self.cpp_info.components["aslcpp"].requires = ["asl-mt" if self.options.with_openmp else "asl"]
