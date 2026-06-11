import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"

class C4CoreConan(ConanFile):
    name = "c4core"
    description = (
        "c4core is a library of low-level C++ utilities, written with "
        "low-latency projects in mind."
    )
    license = "MIT",
    homepage = "https://github.com/biojppm/c4core"
    topics = ("utilities", "low-latency", )
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_fast_float": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_fast_float": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_fast_float:
            self.requires("fast_float/[<9]", transitive_headers=True)

    def validate(self):
        check_min_cppstd(self, "11")

        ## clang with libc++ is not supported. It is already fixed since 0.1.9.
        if Version(self.version) <= "0.1.8":
            if self.settings.compiler in ["clang", "apple-clang"] and \
                self.settings.compiler.get_safe("libcxx") == "libc++":
                raise ConanInvalidConfiguration(f"{self.ref} doesn't support clang with libc++")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["C4CORE_WITH_FASTFLOAT"] = bool(self.options.with_fast_float)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE*", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rm(self, "*.natvis", os.path.join(self.package_folder, "include"), recursive=True)

    def package_info(self):
        self.cpp_info.libs = ["c4core"]
        if not self.options.with_fast_float:
            self.cpp_info.defines.append("C4CORE_NO_FAST_FLOAT")

        self.cpp_info.set_property("cmake_file_name", "c4core")
        self.cpp_info.set_property("cmake_target_name", "c4core::c4core")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
