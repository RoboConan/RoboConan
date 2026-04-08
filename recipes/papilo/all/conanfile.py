import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class PapiloConan(ConanFile):
    name = "papilo"
    description = "PaPILO: Parallel Presolve for Integer and Linear Optimization"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/scipopt/papilo"
    topics = ("optimization", "presolving", "linear-programming", "mixed-integer-programming")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "tools": [True, False],
        "quadmath": [True, False],
        "with_gmp": [True, False],
        "with_gurobi": [True, False],
        "with_highs": [True, False],
        "with_lusol": [True, False],
        "with_ortools": [True, False],
        "with_roundingsat": [True, False],
        "with_scip": [True, False],
        "with_soplex": [True, False],
        "with_tbb": [True, False],
    }
    default_options = {
        "fPIC": True,
        "tools": False,
        "quadmath": True,
        "with_lusol": True,
        "with_tbb": True,
        "with_gmp": False,
        "with_ortools": False,
        # Only used for the papilo executable
        "with_gurobi": False,
        "with_highs": False,
        "with_roundingsat": False,
        "with_scip": False,
        "with_soplex": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        self.options.quadmath = self.settings.get_safe("compiler.libcxx") in ["libstdc++", "libstdc++11"]

    def configure(self):
        if not self.options.tools:
            del self.options.with_gurobi
            del self.options.with_highs
            del self.options.with_roundingsat
            del self.options.with_scip
            del self.options.with_soplex
        if self.options.get_safe("with_roundingsat"):
            self.options["roundingsat"].with_gmp = self.options.with_gmp
            self.options["roundingsat"].with_soplex = self.options.with_soplex
        self.options["boost"].with_iostreams = True
        self.options["boost"].with_program_options = True
        self.options["boost"].with_serialization = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.65]", transitive_headers=True, transitive_libs=True)
        self.requires("skarupke-flat-hash-map/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("pdqsort/[*]", transitive_headers=True, transitive_libs=True)
        fmt_range = "<9" if self.options.tools else "<10"
        self.requires(f"fmt/[{fmt_range}]", transitive_headers=True, transitive_libs=True)
        if self.options.with_tbb:
            self.requires("onetbb/[>=2018]", transitive_headers=True, transitive_libs=True)
        if self.options.with_gmp:
            self.requires("gmp/[^6.0]")
        if self.options.with_lusol:
            self.requires("lusol/[*]", transitive_headers=True)
        if self.options.with_ortools:
            self.requires("or-tools/[>=9.0 <10]", transitive_headers=True, transitive_libs=True)
        if self.options.tools:
            if self.options.with_scip:
                self.requires("scip/[>=8.0 <10]")
            if self.options.with_soplex:
                self.requires("soplex/[>=6.0 <8]")
            if self.options.with_highs:
                self.requires("highs/[^1]")
            if self.options.with_gurobi:
                self.requires("gurobi/[*]")
            if self.options.with_roundingsat:
                self.requires("roundingsat/[<0.0+git.20250909]")

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD", "# set(CMAKE_CXX_STANDARD")
        rmdir(self, "src/papilo/external")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["PAPILO_NO_BINARIES"] = not self.options.tools
        tc.cache_variables["GLOP"] = self.options.with_ortools
        tc.cache_variables["GMP"] = self.options.with_gmp
        tc.cache_variables["GUROBI"] = self.options.get_safe("with_gurobi", False)
        tc.cache_variables["HIGHS"] = self.options.get_safe("with_highs", False)
        tc.cache_variables["LUSOL"] = self.options.with_lusol
        tc.cache_variables["QUADMATH"] = self.options.quadmath
        tc.cache_variables["ROUNDINGSAT"] = self.options.get_safe("with_roundingsat", False)
        tc.cache_variables["SCIP"] = self.options.get_safe("with_scip", False)
        tc.cache_variables["SOPLEX"] = self.options.get_safe("with_soplex", False)
        tc.cache_variables["TBB"] = self.options.with_tbb
        tc.cache_variables["PAPILO_BYTELL_HASHMAP_WORKS"] = True
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("gmp", "cmake_file_name", "GMP")
        deps.set_property("gurobi", "cmake_file_name", "GUROBI")
        deps.set_property("onetbb", "cmake_file_name", "TBB")
        deps.set_property("or-tools", "cmake_file_name", "GLOP")
        deps.set_property("scip", "cmake_file_name", "SCIP")
        deps.set_property("soplex", "cmake_file_name", "SOPLEX")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "papilo")
        self.cpp_info.components["core"].set_property("cmake_target_name", "papilo")
        self.cpp_info.components["core"].libs = ["papilo-core" if self.settings.compiler != "msvc" else "libpapilo-core"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["core"].system_libs = ["m", "rt", "pthread", "dl"]
        self.cpp_info.components["core"].requires = [
            "boost::iostreams",
            "boost::program_options",
            "boost::serialization",
            "skarupke-flat-hash-map::skarupke-flat-hash-map",
            "pdqsort::pdqsort",
            "fmt::fmt",
        ]
        if self.options.with_tbb:
            self.cpp_info.components["core"].requires.append("onetbb::onetbb")
        if self.options.with_gmp:
            self.cpp_info.components["core"].requires.append("gmp::gmp")
        if self.options.with_lusol:
            self.cpp_info.components["core"].requires.append("lusol::lusol")
        if self.options.with_ortools:
            self.cpp_info.components["core"].requires.append("or-tools::or-tools")

        if self.options.tools:
            requires = []
            if self.options.with_scip:
                requires.append("scip::scip")
            if self.options.with_soplex:
                requires.append("soplex::soplex")
            if self.options.with_highs:
                requires.append("highs::highs")
            if self.options.with_gurobi:
                requires.append("gurobi::gurobi")
            if self.options.with_roundingsat:
                requires.append("roundingsat::roundingsat")
            self.cpp_info.components["_executable"].requires = requires
