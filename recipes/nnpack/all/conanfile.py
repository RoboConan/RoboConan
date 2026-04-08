import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class NnpackConan(ConanFile):
    name = "nnpack"
    description = "Acceleration package for neural networks on multi-core CPUs"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Maratyszcza/NNPACK"
    topics = ("neural-networks", "deep-learning", "simd", "performance")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "backend": ["auto", "psimd", "scalar", "neon"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "backend": "auto",
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.arch).startswith("arm"):
            self.options.backend = "neon"
        elif self.settings.os == "Emscripten":
            self.options.backend = "scalar"
        else:
            self.options.backend = "psimd"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("pthreadpool/[>=0.0+git.20231129]", transitive_headers=True)
        self.requires("cpuinfo/[>=0.0+git.20231129]")
        self.requires("fp16/[>=0.0+git.20210320]")
        self.requires("fxdiv/[>=0.0+git.20200417]")
        if self.options.backend == "psimd":
            self.requires("psimd/[>=0.0+git.20200517]")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)
        if self.options.backend == "neon" and not str(self.settings.arch).startswith("arm"):
            raise ConanInvalidConfiguration("NEON backend requires ARM architecture")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "CXX_STANDARD 11", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["NNPACK_LIBRARY_TYPE"] = "shared" if self.options.shared else "static"
        tc.cache_variables["NNPACK_BACKEND"] = self.options.backend
        tc.cache_variables["NNPACK_BUILD_TESTS"] = False
        tc.generate()

        deps = CMakeDeps(self)
        for dep in ["cpuinfo", "fp16", "fxdiv", "pthreadpool", "psimd"]:
            deps.set_property(dep, "cmake_target_name", dep)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["nnpack"]
        if not self.options.shared:
            self.cpp_info.libs.append("nnpack_reference_layers")
        self.cpp_info.includedirs = ["include"]
        if self.options.backend == "psimd":
            self.cpp_info.defines.append("NNP_BACKEND_PSIMD=1")
        elif self.options.backend == "scalar":
            self.cpp_info.defines.append("NNP_BACKEND_SCALAR=1")
        if not self.options.shared and self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
