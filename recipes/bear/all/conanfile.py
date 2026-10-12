import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class BearConan(ConanFile):
    name = "bear"
    description = "Bear is a tool that generates a compilation database for clang tooling"
    license = "GPL-3.0-only"
    homepage = "https://github.com/rizsotto/Bear"
    topics = ("clang", "compilation", "database", "llvm")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("grpc/[^1.50.2]")
        self.requires("nlohmann_json/[^3]")
        self.requires("spdlog/[^1.10]")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("grpc/<host_version>")
        # Older versions of CMake fail to build object libraries in the correct order
        self.tool_requires("cmake/[>=3.20 <5]")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} cannot be built on windows.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_UNIT_TESTS"] = False
        tc.variables["ENABLE_FUNC_TESTS"] = False
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="source")
        cmake.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # Bear is not really relocatable at the moment due to relying on hard-coded CMake install paths.
        # https://github.com/rizsotto/Bear/blob/3.1.5/source/config.h.in#L110-L111
        # Relocated paths can only be provided via command line arguments as of v3.1.6.
        bear = os.path.join(self.package_folder, "bin", "bear")
        wrapper = os.path.join(self.package_folder, "lib", "bear", "wrapper")
        wrapper_dir = os.path.join(self.package_folder, "lib", "bear", "wrapper.d")
        preload_library = os.path.join(self.package_folder, "lib", "bear", "libexec.so")
        self.conf_info.define_path("user.bear:bear", bear)
        self.conf_info.define_path("user.bear:wrapper", wrapper)
        self.conf_info.define_path("user.bear:wrapper-dir", wrapper_dir)
        self.conf_info.define_path("user.bear:preload-library", preload_library)
        self.conf_info.define("user.bear:command", " ".join([
            "bear",
            "--bear-path", f"'{bear}'",
            "--library", f"'{preload_library}'",
            "--wrapper", f"'{wrapper}'",
            "--wrapper-dir", f"'{wrapper_dir}'",
        ]))
