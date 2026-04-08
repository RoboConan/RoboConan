import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SCIPConan(ConanFile):
    name = "scip"
    description = "SCIP mixed integer (nonlinear) programming solver"
    license = "Apache-2.0"
    homepage = "https://scipopt.org/"
    topics = ("mip", "solver", "linear", "programming")
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "threading": ["none", "omp", "tny"],
        "lp_solver": ["clp", "cplex", "gurobi", "highs", "mosek", "xpress", "soplex"],
        "sym": ["none", "bliss", "sbliss", "nauty", "snauty", "dejavu"],
        "with_ampl": [True, False],
        "with_gmp": [True, False],
        "with_ipopt": [True, False],
        "with_lapack": [True, False],
        "with_papilo": [True, False],
        "with_readline": [True, False],
        "with_worhp": [True, False],
        "with_zimpl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "threading": "omp",
        "lp_solver": "highs",
        "sym": "snauty",
        "with_ampl": False,
        "with_gmp": True,
        "with_ipopt": True,
        "with_lapack": True,
        "with_papilo": True,
        "with_readline": False,
        "with_worhp": False,
        "with_zimpl": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if Version(self.version) < "9.0":
            # snauty is not available for older versions
            self.options.sym = "sbliss"
            # highs is not available for older versions
            self.options.lp_solver = "soplex"
            del self.options.with_lapack

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["soplex"].with_gmp = self.options.with_gmp
        if self.options.with_papilo:
            self.options["boost"].with_iostreams = True
            self.options["boost"].with_program_options = True
            self.options["boost"].with_serialization = True
            self.options["boost"].with_random = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_ampl:
            self.requires("ampl-mp/[^4]")
        if self.options.with_ipopt:
            self.requires("coin-ipopt/[^3]")
        if self.options.with_gmp:
            self.requires("gmp/[^6.3.0]")
        if self.options.get_safe("with_lapack"):
            self.requires("lapack/latest")
        if self.options.with_papilo:
            self.requires("papilo/[>=2 <4]")
        if self.options.with_readline:
            self.requires("readline/[^8.1]")
        if self.options.with_worhp:
            self.requires("worhp/[^1]")
        if self.options.with_zimpl:
            self.requires("zimpl/[^3]")
        # For an upcoming release
        # if self.options.with_conopt:
        #     self.requires("conopt/[^4.0]")

        # LP Solver dependencies
        if self.options.lp_solver == "clp":
            self.requires("coin-clp/[^1]")
        elif self.options.lp_solver == "cplex":
            self.requires("cplex/[*]")
        elif self.options.lp_solver == "gurobi":
            self.requires("gurobi/[*]")
        elif self.options.lp_solver == "highs":
            self.requires("highs/[^1]")
        elif self.options.lp_solver == "mosek":
            self.requires("mosek/[*]")
        elif self.options.lp_solver == "soplex":
            self.requires("soplex/[*]")
        elif self.options.lp_solver == "xpress":
            self.requires("xpress/[*]")

        # Symmetry computation dependencies
        if self.options.sym in ["bliss", "sbliss"]:
            self.requires("bliss/[>=0.77 <1]")
        elif self.options.sym in ["nauty", "snauty"]:
            self.requires("nauty/[^2.9.1]")
        if self.options.sym in ["sbliss", "snauty"]:
            self.requires("sassy/[*]", transitive_headers=True)

        # Threading dependencies
        if self.options.threading == "omp":
            self.requires("openmp/system")
        elif self.options.threading == "tny":
            self.requires("tinycthread/[*]")

        # CppAD cannot be unvendored as it's quite old (20180000.0) and with modifications

    def validate(self):
        check_min_cppstd(self, 14)
        if is_msvc(self) and self.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} cannot be built as shared on MSVC.")
        if self.options.lp_solver == "soplex":
            if self.dependencies["soplex"].options.with_gmp and not self.options.with_gmp:
                raise ConanInvalidConfiguration("The options 'with_gmp' should be aligned with 'soplex:with_gmp' too.")
        if Version(self.version) < "10.0" and self.options.sym == "dejavu":
            raise ConanInvalidConfiguration("Symmetry option 'dejavu' is only supported in SCIP v10 and above.")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD", "# set(CMAKE_CXX_STANDARD")

        # Remove all non-sanitizer find modules
        for f in Path("cmake/Modules").glob("Find*.cmake"):
            if "San" not in f.name:
                f.unlink()

        # Unvendor
        rmdir(self, "src/amplmp")
        rmdir(self, "src/nauty")
        rmdir(self, "src/sassy")
        rmdir(self, "src/tinycthread")
        replace_in_file(self, "src/CMakeLists.txt", "install(FILES ${tinycthreadheader}", "# ")

        tny_files = [
            "src/lpi/lpi_grb.c",
            "src/lpi/lpi_msk.c",
            "src/lpi/lpi_xprs.c",
            "src/tpi/type_tpi_tnycthrd.h",
        ]
        if Version(self.version) >= "9.0":
            tny_files.append("src/tpi/tpi_tnycthrd.c")
        for f in tny_files:
            replace_in_file(self, f, "tinycthread/tinycthread.h", "tinycthread.h")

        replace_in_file(self, "src/symmetry/compute_symmetry_nauty.c", "nauty/", "")
        if Version(self.version) >= "9.0":
            replace_in_file(self, "src/symmetry/compute_symmetry_sassy_nauty.cpp", "nauty/", "")
            replace_in_file(self, "src/symmetry/compute_symmetry_nauty.c", '#include "tinycthread/tinycthread.h"', "")
            replace_in_file(self, "src/symmetry/compute_symmetry_sassy_nauty.cpp", '#include "tinycthread/tinycthread.h"', "")

        # Don't embed build-time paths in RPATHS
        replace_in_file(self, "src/CMakeLists.txt", "INSTALL_RPATH_USE_LINK_PATH TRUE", "")
        replace_in_file(self, "src/CMakeLists.txt", "set_target_properties(scip PROPERTIES", "message(TRACE ")

    @property
    def _lp_solver(self):
        return {
            "clp": "clp",
            "cplex": "cpx",
            "gurobi": "grb",
            "highs": "highs",
            "mosek": "msk",
            "soplex": "spx",
            "xpress": "xprs",
        }[str(self.options.lp_solver)]

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["AUTOBUILD"] = False
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["SHARED"] = self.options.shared
        tc.cache_variables["ZLIB"] = True
        tc.cache_variables["READLINE"] = self.options.get_safe("with_readline", False)
        tc.cache_variables["GMP"] = self.options.with_gmp
        tc.cache_variables["STATIC_GMP"] = self.options.with_gmp and not self.dependencies["gmp"].options.shared
        tc.cache_variables["PAPILO"] = self.options.with_papilo
        tc.cache_variables["ZIMPL"] = self.options.with_zimpl
        tc.cache_variables["AMPL"] = self.options.with_ampl
        tc.cache_variables["IPOPT"] = self.options.with_ipopt
        tc.cache_variables["LAPACK"] = self.options.get_safe("with_lapack", False)
        tc.cache_variables["WORHP"] = self.options.with_worhp
        tc.cache_variables["CONOPT"] = self.options.get_safe("with_conopt", False)
        tc.cache_variables["THREADSAFE"] = True
        tc.cache_variables["LPS"] = self._lp_solver
        tc.cache_variables["SYM"] = self.options.sym
        tc.cache_variables["TPI"] = self.options.threading
        tc.cache_variables["MT"] = is_msvc_static_runtime(self)
        tc.cache_variables["Readline_LIBRARY"] = "readline::readline"
        tc.cache_variables["SOPLEX_INCLUDE_DIRS"] = ";"
        tc.cache_variables["SOPLEX_LIBRARIES"] = "soplex"
        tc.cache_variables["SOPLEX_PIC_LIBRARIES"] = "soplex"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("coin-clp", "cmake_file_name", "CLP")
        deps.set_property("cplex", "cmake_file_name", "CPLEX")
        deps.set_property("gmp", "cmake_file_name", "GMP")
        deps.set_property("gurobi", "cmake_file_name", "GUROBI")
        deps.set_property("coin-ipopt", "cmake_file_name", "IPOPT")
        deps.set_property("mosek", "cmake_file_name", "MOSEK")
        deps.set_property("or-tools", "cmake_file_name", "GLOP")
        deps.set_property("papilo", "cmake_file_name", "PAPILO")
        deps.set_property("qsopt", "cmake_file_name", "QSO")
        deps.set_property("readline", "cmake_file_name", "Readline")
        deps.set_property("soplex", "cmake_file_name", "SOPLEX")
        deps.set_property("worhp", "cmake_file_name", "WORHP")
        deps.set_property("xpress", "cmake_file_name", "XPRESS")
        deps.generate()

    def _patch_sources(self):
        if not self.options.tools:
            replace_in_file(self, os.path.join(self.source_folder, "src/CMakeLists.txt"),
                            "install(TARGETS scip libscip",
                            "install(TARGETS libscip")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        if self.options.tools:
            cmake.build()
        else:
            cmake.build(target="libscip")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "scip")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["SCIP"])
        self.cpp_info.set_property("cmake_target_aliases", ["libscip"])
        self.cpp_info.libs = ["libscip" if is_msvc(self) else "scip"]
