import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.13"


class SleqpConan(ConanFile):
    name = "sleqp"
    description = "Active set-based NLP solver for large-scale nonlinear continuous optimization."
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/chrhansk/sleqp"
    topics = ("optimization", "nonlinear-optimization", "active-set")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # The LP solver and factorization backends are ordered by their order of preference in the project
        "lp_solver": ["gurobi", "highs", "soplex"],
        "fact_backend": ["umfpack", "spqr", "cholmod", "mumps", "ma27", "ma57", "ma86", "ma97", "lapack"],
        "with_asl": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "lp_solver": "highs",
        "fact_backend": "umfpack",
        "with_asl": False,
        "with_openmp": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("trlib/[>=0.4 <1]")
        if self.options.with_asl:
            self.requires("ampl-asl/[^1]")
        if self.options.with_openmp:
            self.requires("openmp/system")

        if self.options.lp_solver == "gurobi":
            self.requires("gurobi/[>=9.0]")
        elif self.options.lp_solver == "highs":
            self.requires("highs/[^1]")
        elif self.options.lp_solver == "soplex":
            self.requires("soplex/[>=6.0 <8]")

        if self.options.fact_backend == "umfpack":
            self.requires("suitesparse-umfpack/[^6]")
        elif self.options.fact_backend == "spqr":
            self.requires("suitesparse-spqr/[<4]")
        elif self.options.fact_backend == "cholmod":
            self.requires("suitesparse-cholmod/[<5]")
        elif self.options.fact_backend == "mumps":
            self.requires("coin-mumps/[^3]")
        elif self.options.fact_backend in ["ma27", "ma57", "ma86", "ma97"]:
            self.requires("coin-hsl/[*]")
        elif self.options.fact_backend == "lapack":
            self.requires("lapack/latest")

    def validate(self):
        if self.options.fact_backend == "lapack":
            mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
            if mangling != "lower_underscore":
                raise ConanInvalidConfiguration("SLEQP requires LAPACK with lower_underscore names")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        save(self, "cmake/SearchFactCHOLMOD.cmake", "find_package(CHOLMOD REQUIRED)")
        save(self, "cmake/SearchFactSPQR.cmake", "find_package(SPQR REQUIRED)")
        save(self, "cmake/SearchFactUmfpack.cmake", "find_package(UMFPACK REQUIRED)")
        save(self, "cmake/SearchFactMUMPS.cmake", "find_package(MUMPS REQUIRED)")
        for algo in ["MA27", "MA57", "MA86", "MA97"]:
            save(self, f"cmake/SearchFact{algo}.cmake",
                 f"find_package(coin-hsl REQUIRED)\n"
                 f"set({algo}_FOUND 1)\n"
                 f"set({algo}_LIBRARIES coin-hsl::coin-hsl)\n")
        save(self, "cmake/SearchLPSGurobi.cmake", "find_package(GUROBI REQUIRED)")
        save(self, "cmake/SearchLPSHighs.cmake", "find_package(HIGHS REQUIRED)")
        save(self, "cmake/SearchLPSSoplex.cmake", "find_package(SOPLEX REQUIRED)")
        replace_in_file(self, "CMakeLists.txt", "pkg_check_modules(COINASL coinasl)", "find_package(COINASL)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["SLEQP_ENABLE_UNIT_TESTS"] = False
        tc.cache_variables["SLEQP_ENABLE_C_UNIT_TESTS"] = False
        tc.cache_variables["SLEQP_ENABLE_CUTEST"] = False
        tc.cache_variables["SLEQP_ENABLE_PYTHON"] = False
        tc.cache_variables["SLEQP_ENABLE_OCTAVE_MEX"] = False
        tc.cache_variables["SLEQP_ENABLE_MATLAB_MEX"] = False
        tc.cache_variables["SLEQP_GENERATE_COVERAGE"] = False
        tc.cache_variables["SLEQP_ENABLE_AMPL"] = self.options.with_asl
        tc.cache_variables["SLEQP_LPS"] = {
            "gurobi": "Gurobi",
            "highs": "HiGHS",
            "soplex": "SoPlex",
        }[str(self.options.lp_solver)]
        tc.cache_variables["SLEQP_FACT"] = {
            "umfpack": "Umfpack",
            "spqr": "SPQR",
            "cholmod": "CHOLMOD",
            "mumps": "MUMPS",
            "ma27": "MA27",
            "ma57": "MA57",
            "ma86": "MA86",
            "ma97": "MA97",
            "lapack": "LAPACK",
        }[str(self.options.fact_backend)]
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("ampl-asl", "cmake_file_name", "COINASL")
        deps.set_property("ampl-asl", "cmake_target_name", "coinasl")
        deps.set_property("coin-mumps", "cmake_file_name", "MUMPS")
        deps.set_property("suitesparse-umfpack", "cmake_file_name", "UMFPACK")
        deps.set_property("gurobi", "cmake_file_name", "GUROBI")
        deps.set_property("highs", "cmake_file_name", "HIGHS")
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
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sleqp")
        self.cpp_info.set_property("cmake_target_name", "sleqp::sleqp")
        self.cpp_info.set_property("pkg_config_name", "sleqp")
        self.cpp_info.libs = ["sleqp"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "rt"]
