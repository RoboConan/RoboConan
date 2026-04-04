import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class CrocoddylConan(ConanFile):
    name = "crocoddyl"
    description = "Crocoddyl is an optimal control library for robot control under contact sequence."
    license = "BSD-3-Clause"
    homepage = "https://github.com/loco-3d/crocoddyl"
    topics = ("robotics", "optimal-control", "differential-dynamic-programming", "contact-dynamics")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "codegen": [True, False],
        "num_threads": ["ANY"],
        "with_openmp": [True, False],
        "with_ipopt": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "codegen": False,
        "num_threads": 10,
        "with_openmp": True,
        "with_ipopt": True,
        "boost/*:with_filesystem": True,
        "boost/*:with_serialization": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_openmp:
            del self.options.num_threads

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("pinocchio/[^3.4.0]", transitive_headers=True, transitive_libs=True)
        self.requires("boost/[^1.71.0]", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        if self.options.with_openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.codegen:
            self.requires("cppadcodegen/[^2.5]")
        if self.options.with_ipopt:
            self.requires("coin-ipopt/[^3.14]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "add_optional_dependency(ipopt)", "find_package(IPOPT REQUIRED)")
        replace_in_file(self, "CMakeLists.txt", 'add_optional_dependency("scipy")', "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_BENCHMARK"] = False
        tc.cache_variables["BUILD_PYTHON_INTERFACE"] = False
        tc.cache_variables["INSTALL_DOCUMENTATION"] = False
        tc.cache_variables["GENERATE_PYTHON_STUBS"] = False
        tc.cache_variables["BUILD_WITH_MULTITHREADS"] = self.options.with_openmp
        tc.cache_variables["BUILD_WITH_NTHREADS"] = self.options.get_safe("num_threads", 0)
        tc.cache_variables["BUILD_WITH_CODEGEN_SUPPORT"] = self.options.codegen
        tc.cache_variables["BUILD_WITH_IPOPT"] = self.options.with_ipopt
        tc.cache_variables["IPOPT_FOUND"] = self.options.with_ipopt
        tc.cache_variables["ENABLE_VECTORIZATION"] = False  # only adds -march=native
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0177"] = "NEW"
        tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("coin-ipopt", "cmake_file_name", "IPOPT")
        deps.set_property("coin-ipopt", "cmake_target_name", "ipopt")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "crocoddyl")
        self.cpp_info.set_property("cmake_target_name", "crocoddyl::crocoddyl")
        self.cpp_info.set_property("pkg_config_name", "crocoddyl")
        self.cpp_info.libs = ["crocoddyl"]
        self.cpp_info.defines = ["PINOCCHIO_ENABLE_COMPATIBILITY_WITH_VERSION_2"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.cpp_info.requires = [
            "pinocchio::pinocchio",
            "boost::filesystem",
            "boost::serialization",
            "eigen::eigen",
        ]
        if self.options.with_openmp:
            self.cpp_info.defines.append("CROCODDYL_WITH_MULTITHREADING")
            self.cpp_info.defines.append(f"CROCODDYL_WITH_NTHREADS={self.options.num_threads}")
            self.cpp_info.requires.append("openmp::openmp")
        if self.options.codegen:
            self.cpp_info.defines.extend([
                "CROCODDYL_WITH_CODEGEN",
                "PINOCCHIO_WITH_CPPAD_SUPPORT",
                "PINOCCHIO_WITH_CPPADCG_SUPPORT"
            ])
            self.cpp_info.requires.append("cppadcodegen::cppadcodegen")
        if self.options.with_ipopt:
            self.cpp_info.defines.append("CROCODDYL_WITH_IPOPT")
            self.cpp_info.requires.append("coin-ipopt::coin-ipopt")
