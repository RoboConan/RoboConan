import os
from functools import cached_property
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class GurobiConan(ConanFile):
    name = "gurobi"
    description = "Gurobi Optimizer C/C++ SDK"
    license = "DocumentRef-EULA.pdf:LicenseRef-GUROBI-EULA"
    homepage = "https://www.gurobi.com/"
    topics = ("optimization", "linear-programming", "mixed-integer-programming", "quadratic-programming")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "cxx": [True, False],
        "tools": [True, False],
    }
    default_options = {
        "shared": False,
        "cxx": True,
        "tools": False,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def configure(self):
        if not self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.cxx:
            self.package_type = "shared-library"
            self.languages = ["C"]
            self.options.rm_safe("shared")

    def package_id(self):
        if not self.info.options.cxx:
            del self.info.settings.compiler
            del self.info.settings.build_type
        if is_apple_os(self.info):
            self.info.settings.arch = "armv8|x86_64"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.settings.arch not in ["x86_64", "armv8"]:
                raise ConanInvalidConfiguration("Only x86_64 and armv8 are supported on Linux")
        elif self.settings.os == "Windows":
            if self.settings.arch != "x86_64":
                raise ConanInvalidConfiguration("Only x86_64 is supported on Windows")
        elif not is_apple_os(self):
            raise ConanInvalidConfiguration("Only Linux, Windows and Macos are supported")
        if self.options.cxx:
            check_min_cppstd(self, 98)

    def build_requirements(self):
        if self.settings.os == "Windows":
            self.tool_requires("lessmsi/[*]")

    def _source(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            info = self.conan_data["sources"][self.version]["Linux"][str(self.settings.arch)]
            get(self, **info, strip_root=True)
        elif is_apple_os(self):
            info = self.conan_data["sources"][self.version]["Macos"]
            path = "gurobi.pkg"
            download(self, **info, filename=path)
            self.run(f"pkgutil --expand-full '{path}' .")
            os.unlink(path)
        else:
            info = self.conan_data["sources"][self.version]["Windows"]
            path = "gurobi.msi"
            download(self, **info, filename=path)
            self.run(f'lessmsi x "{path}"')
            os.unlink(path)
        package_root = next(Path(self.build_folder).rglob("EULA.pdf")).parent
        move_folder_contents(self, package_root, self.source_folder)
        if self.options.cxx:
            copy(self, "CMakeLists.txt", self.export_sources_folder, self.source_folder)

    @cached_property
    def _c_lib(self):
        v = Version(self.version)
        return f"gurobi{v.major}{v.minor}"

    def generate(self):
        if self.options.cxx:
            tc = CMakeToolchain(self)
            tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
            tc.cache_variables["C_LIB"] = self._c_lib
            tc.generate()

    def build(self):
        self._source()
        if self.options.cxx:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        copy(self, "EULA.pdf", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "gurobi_c.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            copy(self, "libgurobi.so*", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
            copy(self, f"lib{self._c_lib}.so", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
        elif is_apple_os(self):
            copy(self, f"lib{self._c_lib}.dylib", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
        else:
            copy(self, f"{self._c_lib}.dll", os.path.join(self.source_folder, "bin"), os.path.join(self.package_folder, "bin"))
            copy(self, f"{self._c_lib}.lib", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
        if self.options.tools:
            copy(self, "grb*", os.path.join(self.source_folder, "bin"), os.path.join(self.package_folder, "bin"))
            copy(self, "gurobi_cl*", os.path.join(self.source_folder, "bin"), os.path.join(self.package_folder, "bin"))
        if self.options.cxx:
            cmake = CMake(self)
            cmake.install()

    def package_info(self):
        self.cpp_info.components["gurobi_c"].libs = [self._c_lib]
        self.cpp_info.components["gurobi_c"].set_property("nosoname", True)

        if self.options.cxx:
            self.cpp_info.components["gurobi_cxx"].libs = ["gurobi_c++"]
            self.cpp_info.components["gurobi_cxx"].requires = ["gurobi_c"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["gurobi_cxx"].system_libs = ["m"]

        self.runenv_info.define_path("GUROBI_HOME", self.package_folder)
