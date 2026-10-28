import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, valid_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class AlpaqaConan(ConanFile):
    name = "alpaqa"
    description = "Augmented Lagrangian and PANOC solvers for nonconvex numerical optimization"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/kul-optec/alpaqa"
    topics = ("optimization", "panoc", "alm", "mpc", "nonlinear-programming")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "precision_single": [True, False],
        "precision_quad": [True, False],
        "precision_longdouble": [True, False],
        "enable_ocp": [True, False],
        "with_blas": [True, False],
        "with_casadi": [True, False],
        "with_cutest": [True, False],
        "with_ipopt": [True, False],
        "with_json": [True, False],
        "with_lbfgsb": [True, False],
        "with_lbfgspp": [True, False],
        "with_openmp": [True, False],
        "with_qpalm": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "precision_single": False,
        "precision_quad": False,
        "precision_longdouble": False,
        "enable_ocp": True,
        "with_blas": True,
        "with_casadi": False,
        "with_cutest": False,
        "with_ipopt": False,
        "with_json": True,
        "with_lbfgsb": False,
        "with_lbfgspp": False,
        "with_openmp": True,
        "with_qpalm": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C++"]

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["eigen"].with_blas = self.options.with_blas
        if not self.options.with_lbfgsb:
            self.settings.rm_safe("fortran")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        self.requires("guanaqo/[^1.0, include_prerelease]", transitive_headers=True)
        if self.options.with_casadi:
            self.requires("casadi/[^3.7]", transitive_headers=True)
        if self.options.with_cutest:
            self.requires("cutest/[*]")
        if self.options.with_json:
            self.requires("nlohmann_json/[^3.12]", transitive_headers=True)
        if self.options.with_ipopt:
            self.requires("coin-ipopt/[^3.14]", transitive_headers=True)
        if self.options.with_qpalm:
            self.requires("qpalm/[^1.2]", transitive_headers=True)
        if self.options.with_lbfgsb:
            self.requires("lbfgsb/[^3.0]")
            self.fortran.requires_runtime()
        if self.options.with_lbfgspp:
            self.requires("lbfgspp/[>=0.4 <1]")
        if self.options.with_blas:
            self.requires("blas/latest")
        if self.options.with_openmp:
            self.requires("openmp/system")

    def validate(self):
        check_min_cppstd(self, 20, gnu_extensions=self.options.precision_quad)
        if self.dependencies["eigen"].options.with_blas != self.options.with_blas:
            raise ConanInvalidConfiguration("alpaqa:with_blas must match eigen:with_blas")
        if self.options.with_cutest:
            check_min_cppstd(self, 23)
        if self.options.with_lbfgsb:
            self.fortran.validate_settings()

    def validate_build(self):
        if self.options.with_lbfgsb:
            self.fortran.validate_build()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.25]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        rmdir(self, "src/thirdparty")
        if Version(self.version) >= "1.1.0":
            replace_in_file(self, "src/cmake/Install.cmake",
                            'alpaqa_add_if_target_exists(ALPAQA_COMPONENT_EXTRA_TARGETS "lbfgsb-fortran")',
                            'alpaqa_add_if_target_exists(ALPAQA_COMPONENT_EXTRA_TARGETS "lbfgspp-adapter")')

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["ALPAQA_WITH_TESTS"] = False
        tc.cache_variables["ALPAQA_WITH_EXAMPLES"] = False
        tc.cache_variables["ALPAQA_WITH_PYTHON"] = False
        tc.cache_variables["ALPAQA_WITH_MATLAB"] = False
        tc.cache_variables["ALPAQA_WITH_PYTHON_PROBLEM_LOADER"] = False
        tc.cache_variables["ALPAQA_WITH_COVERAGE"] = False
        tc.cache_variables["ALPAQA_WITH_DRIVERS"] = self.options.tools
        tc.cache_variables["ALPAQA_WITH_CXX_23"] = valid_min_cppstd(self, 23)
        tc.cache_variables["ALPAQA_WITH_QUAD_PRECISION"] = self.options.precision_quad
        tc.cache_variables["ALPAQA_WITH_SINGLE_PRECISION"] = self.options.precision_single
        tc.cache_variables["ALPAQA_WITH_LONG_DOUBLE"] = self.options.precision_longdouble
        tc.cache_variables["ALPAQA_DONT_PARALLELIZE_EIGEN"] = False
        tc.cache_variables["ALPAQA_WITH_BLAS"] = self.options.with_blas
        tc.cache_variables["ALPAQA_WITH_CASADI"] = self.options.with_casadi
        tc.cache_variables["ALPAQA_WITH_CASADI_OCP"] = self.options.enable_ocp and self.options.with_casadi
        tc.cache_variables["ALPAQA_WITH_CUTEST"] = self.options.with_cutest
        tc.cache_variables["ALPAQA_WITH_EXTERNAL_CASADI"] = True
        tc.cache_variables["ALPAQA_WITH_IPOPT"] = self.options.with_ipopt
        tc.cache_variables["ALPAQA_WITH_JSON"] = self.options.with_json
        tc.cache_variables["ALPAQA_WITH_LBFGSB"] = self.options.with_lbfgsb
        tc.cache_variables["ALPAQA_WITH_OCP"] = self.options.enable_ocp
        tc.cache_variables["ALPAQA_WITH_OPENMP"] = self.options.with_openmp
        tc.cache_variables["ALPAQA_WITH_QPALM"] = self.options.with_qpalm
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("cutest", "cmake_file_name", "CUTEst")
        deps.set_property("coin-ipopt", "cmake_file_name", "Ipopt")
        deps.set_property("coin-ipopt", "cmake_target_name", "Ipopt::Ipopt")
        deps.set_property("lbfgsb", "cmake_target_name", "lbfgsb-fortran")
        deps.generate()

    def build(self):
        replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"),
                        "find_package(lbfgspp QUIET)",
                        "find_package(lbfgspp REQUIRED)" if self.options.with_lbfgspp else "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "alpaqa")

        self.cpp_info.components["core"].set_property("cmake_target_name", "alpaqa::alpaqa")
        self.cpp_info.components["core"].libs = ["alpaqa"]
        self.cpp_info.components["core"].requires = ["eigen::eigen", "guanaqo::guanaqo"]
        if self.options.precision_quad:
            self.cpp_info.components["core"].defines.append("ALPAQA_WITH_QUAD_PRECISION")
            self.cpp_info.components["core"].system_libs.append("quadmath")
        if self.options.precision_single:
            self.cpp_info.components["core"].defines.append("ALPAQA_WITH_SINGLE_PRECISION")
        if self.options.precision_longdouble:
            self.cpp_info.components["core"].defines.append("ALPAQA_WITH_LONG_DOUBLE")
        if self.options.with_json:
            self.cpp_info.components["core"].defines.append("ALPAQA_WITH_JSON")
        if self.options.enable_ocp:
            self.cpp_info.components["core"].defines.append("ALPAQA_WITH_OCP")
        if self.options.with_blas:
            self.cpp_info.components["core"].requires.append("blas::blas")
        if self.options.with_openmp:
            self.cpp_info.components["core"].requires.append("openmp::openmp")
        if self.options.with_json:
            self.cpp_info.components["core"].requires.append("nlohmann_json::nlohmann_json")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["core"].system_libs = ["m", "pthread", "dl"]

        # CasADi loader component
        if self.options.with_casadi:
            self.cpp_info.components["casadi-loader"].set_property("cmake_target_name", "alpaqa::casadi-loader")
            self.cpp_info.components["casadi-loader"].libs = ["alpaqa-casadi-loader"]
            self.cpp_info.components["casadi-loader"].requires = ["core", "casadi::casadi"]
            self.cpp_info.components["casadi-loader"].defines = ["ALPAQA_WITH_CASADI", "ALPAQA_WITH_EXTERNAL_CASADI"]

            # CasADi OCP loader component
            if self.options.enable_ocp:
                self.cpp_info.components["casadi-ocp-loader"].set_property("cmake_target_name", "alpaqa::casadi-ocp-loader")
                self.cpp_info.components["casadi-ocp-loader"].libs = ["alpaqa-casadi-ocp-loader"]
                self.cpp_info.components["casadi-ocp-loader"].requires = ["core", "casadi-loader"]
                self.cpp_info.components["casadi-loader"].defines.append("ALPAQA_WITH_CASADI_OCP")

        # Dynamic library loader component
        self.cpp_info.components["dl-loader"].set_property("cmake_target_name", "alpaqa::dl-loader")
        self.cpp_info.components["dl-loader"].libs = ["alpaqa-dl-loader"]
        self.cpp_info.components["dl-loader"].requires = ["core"]
        self.cpp_info.components["dl-loader"].defines = ["ALPAQA_WITH_DL"]

        # CUTEst interface component
        if self.options.with_cutest:
            self.cpp_info.components["cutest-interface"].set_property("cmake_target_name", "alpaqa::cutest-interface")
            self.cpp_info.components["cutest-interface"].libs = ["alpaqa-cutest-interface"]
            self.cpp_info.components["cutest-interface"].requires = ["core", "cutest::cutest"]
            self.cpp_info.components["cutest-interface"].defines = ["ALPAQA_WITH_CUTEST"]

        # Ipopt adapter component
        if self.options.with_ipopt:
            self.cpp_info.components["ipopt-adapter"].set_property("cmake_target_name", "alpaqa::ipopt-adapter")
            self.cpp_info.components["ipopt-adapter"].libs = ["alpaqa-ipopt-adapter"]
            self.cpp_info.components["ipopt-adapter"].requires = ["core", "coin-ipopt::coin-ipopt"]
            self.cpp_info.components["ipopt-adapter"].defines = ["ALPAQA_WITH_IPOPT"]

        # QPALM adapter component
        if self.options.with_qpalm:
            self.cpp_info.components["qpalm-adapter"].set_property("cmake_target_name", "alpaqa::qpalm-adapter")
            self.cpp_info.components["qpalm-adapter"].libs = ["alpaqa-qpalm-adapter"]
            self.cpp_info.components["qpalm-adapter"].requires = ["core", "qpalm::qpalm"]

        # L-BFGS-B adapter component
        if self.options.with_lbfgsb:
            self.cpp_info.components["lbfgsb-adapter"].set_property("cmake_target_name", "alpaqa::lbfgsb-adapter")
            self.cpp_info.components["lbfgsb-adapter"].libs = ["alpaqa-lbfgsb-adapter"]
            self.cpp_info.components["lbfgsb-adapter"].requires = ["core", "lbfgsb::lbfgsb"]
            self.fortran.add_runtime_to_cpp_info(self.cpp_info.components["lbfgsb-adapter"])
            self.cpp_info.components["lbfgsb-adapter"].defines = ["ALPAQA_WITH_LBFGSB"]

        # LBFGS++ adapter component
        if self.options.with_lbfgspp:
            self.cpp_info.components["lbfgspp-adapter"].set_property("cmake_target_name", "alpaqa::lbfgspp-adapter")
            self.cpp_info.components["lbfgspp-adapter"].libs = ["alpaqa-lbfgspp-adapter"]
            self.cpp_info.components["lbfgspp-adapter"].requires = ["core", "lbfgspp::lbfgspp"]
            self.cpp_info.components["lbfgspp-adapter"].defines = ["ALPAQA_WITH_LBFGSPP"]
