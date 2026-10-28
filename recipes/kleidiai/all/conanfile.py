import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class KleidiAIConan(ConanFile):
    name = "kleidiai"
    description = ("KleidiAI is an open-source library that provides optimized performance-critical routines, "
                   "also known as micro-kernels, for artificial intelligence (AI) workloads tailored for Arm CPUs.")
    license = "Apache-2.0 AND BSD-3-Clause"
    homepage = "https://gitlab.arm.com/kleidi/kleidiai"
    topics = ("arm", "micro-kernels", "ai", "machine-learning")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "experimental_ops": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "experimental_ops": False,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if Version(self.version) < "1.30":
            self.options.rm_safe("experimental_ops")

    def validate(self):
        # Uses -march=armv8.2-a to build most of its micro-kernels
        if not str(self.settings.arch).startswith("arm"):
            raise ConanInvalidConfiguration("Only Arm architectures are supported.")
        check_min_cppstd(self, 14)
        if self.settings.compiler.get_safe("cstd"):
            check_min_cstd(self, 99)
        if self.options.get_safe("experimental_ops"):
            if not str(self.settings.arch).startswith("armv8"):
                raise ConanInvalidConfiguration("Experimental ops require Arm64.")
            if self.settings.compiler == "msvc":
                raise ConanInvalidConfiguration("Experimental ops do not support MSVC.")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        rmdir(self, "third_party")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["KLEIDIAI_BUILD_TESTS"] = False
        if Version(self.version) >= "1.30":
            tc.cache_variables["KLEIDIAI_BUILD_EXPERIMENTAL_OPS"] = self.options.experimental_ops
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "*", os.path.join(self.source_folder, "LICENSES"), os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "KleidiAI")
        if Version(self.version) < "1.30":
            self.cpp_info.set_property("cmake_target_name", "KleidiAI::kleidiai")
            self.cpp_info.libs = ["kleidiai"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs = ["dl"]
            return

        self.cpp_info.components["core"].set_property("cmake_target_name", "KleidiAI::kleidiai")
        self.cpp_info.components["core"].libs = ["kleidiai"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["core"].system_libs = ["dl"]

        cmake_file_names = {"KleidiAI": {"components": ["core"]}}
        if self.options.experimental_ops:
            self.cpp_info.components["ops"].set_property("cmake_target_name", "KleidiAIOps::kleidiai_ops")
            self.cpp_info.components["ops"].includedirs = ["include/KleidiAIOps"]
            self.cpp_info.components["ops"].libs = ["kleidiai_ops"]
            cmake_file_names["KleidiAIOps"] = {"components": ["ops"]}
        self.cpp_info.set_property("cmake_file_names", cmake_file_names)
