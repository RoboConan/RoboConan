import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, can_run
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class PinocchioConan(ConanFile):
    name = "pinocchio"
    description = "A fast and flexible implementation of Rigid Body Dynamics algorithms and their analytical derivatives"
    license = "BSD 2-Clause"
    homepage = "https://stack-of-tasks.github.io/pinocchio/"
    topics = ("robotics", "kinematics", "dynamics", "automatic-differentiation",
              "motion-planning", "rigid-body-dynamics", "analytical-derivatives")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_template_instantiation": [True, False],
        "build_python_parser": [True, False],
        "with_urdfdom": [True, False],
        "with_coal": [True, False],
        "with_cppad": [True, False],
        "with_codegen": [True, False],
        "with_casadi": [True, False],
        "with_openmp": [True, False],
        "with_qhull": [True, False],
        # Python module options
        "python_bindings": [True, False],
        "generate_python_stubs": [True, False],
        "with_mpfr": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_template_instantiation": False,  # Disabled for a faster build
        "build_python_parser": False,
        "with_urdfdom": True,
        "with_coal": False,
        "with_cppad": False,
        "with_codegen": False,
        "with_casadi": False,
        "with_openmp": True,
        "with_qhull": False,

        # Python module options
        "python_bindings": False,
        "generate_python_stubs": True,
        "with_mpfr": True,

        "boost/*:with_chrono": True,
        "boost/*:with_date_time": True,
        "boost/*:with_filesystem": True,
        "boost/*:with_serialization": True,
        "boost/*:with_thread": True,
        "coal/*:hpp_fcl_compatibility": True,
        "qhull/*:qhullcpp": True,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cppad:
            self.options.rm_safe("with_codegen")
        if self.options.python_bindings:
            self.options.build_python_parser.value = True
            self.options["boost"].with_python = True
            self.options["boost"].numpy = True
            if self.options.with_coal:
                self.options["coal"].python_bindings = True
        else:
            del self.options.generate_python_stubs
            del self.options.with_mpfr

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        self.requires("boost/[^1.71.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_coal:
            self.requires("coal/[^3.0.1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_urdfdom:
            self.requires("urdfdom/[^4.0.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_cppad:
            self.requires("cppad/[>=20180000]", transitive_headers=True, transitive_libs=True)
            if self.options.with_codegen:
                self.requires("cppadcodegen/[^2.4.1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_casadi:
            self.requires("casadi/[^3.6.6]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openmp:
            # #pragma omp is used in algorithm/parallel public headers
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.with_qhull:
            self.requires("qhull/[^8.1]")
        if self.options.python_bindings:
            # eigenpy adds cpython and numpy deps transitively
            self.requires("eigenpy/[^3.11.0]", transitive_headers=True, transitive_libs=True)
            if self.options.with_mpfr:
                self.requires("gmp/[^6.1.2]")
                self.requires("mpfr/[^4.0.2]")
        if self.options.build_python_parser:
            self.requires("cpython/[^3]")

    def build_requirements(self):
        self.tool_requires("jrl-cmakemodules/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.python_bindings:
            self.tool_requires("eigenpy/[^3.11.0]")
            self.tool_requires("numpy/[^2.0]")
        elif self.options.build_python_parser:
            self.tool_requires("cpython/<host_version>")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.options.with_qhull and not self.dependencies["qhull"].options.qhullcpp:
            raise ConanInvalidConfiguration("-o qhull/*:qhullcpp=True is required")
        for mod in ["chrono", "date_time", "filesystem", "serialization", "thread"]:
            if not self.dependencies["boost"].options.get_safe(f"with_{mod}"):
                raise ConanInvalidConfiguration(f"boost/*:with_{mod}=True is required")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # get jrl-cmakemodules from Conan
        replace_in_file(self, "CMakeLists.txt", "set(JRL_CMAKE_MODULES ", " # set(JRL_CMAKE_MODULES ")
        # Ensure tests and examples are not built
        save(self, "unittest/CMakeLists.txt", "")
        save(self, "examples/CMakeLists.txt", "")
        # Don't install Python bindings to an absolute system path
        replace_in_file(self, "bindings/python/CMakeLists.txt",
                        "set(PINOCCHIO_PYTHON_INSTALL_DIR ${ABSOLUTE_PYTHON_SITELIB}/${PROJECT_NAME})",
                        "set(PINOCCHIO_PYTHON_INSTALL_DIR ${PYTHON_SITELIB}/${PROJECT_NAME})")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_BENCHMARK"] = False
        tc.cache_variables["BUILDING_ROS2_PACKAGE"] = False
        tc.cache_variables["ENABLE_TEMPLATE_INSTANTIATION"] = self.options.enable_template_instantiation
        tc.cache_variables["BUILD_WITH_PYTHON_PARSER_SUPPORT"] = self.options.build_python_parser
        tc.cache_variables["BUILD_WITH_HPP_FCL_SUPPORT"] = self.options.with_coal
        tc.cache_variables["BUILD_WITH_URDF_SUPPORT"] = self.options.with_urdfdom
        tc.cache_variables["BUILD_WITH_AUTODIFF_SUPPORT"] = self.options.with_cppad
        tc.cache_variables["BUILD_WITH_CODEGEN_SUPPORT"] = self.options.get_safe("with_codegen", False)
        tc.cache_variables["BUILD_WITH_CASADI_SUPPORT"] = self.options.with_casadi
        tc.cache_variables["BUILD_WITH_OPENMP_SUPPORT"] = self.options.with_openmp
        tc.cache_variables["BUILD_WITH_EXTRA_SUPPORT"] = self.options.with_qhull
        # Python module options
        tc.cache_variables["BUILD_PYTHON_INTERFACE"] = self.options.python_bindings
        tc.cache_variables["GENERATE_PYTHON_STUBS"] = self.options.get_safe("generate_python_stubs")
        tc.cache_variables["BUILD_WITH_ACCELERATE_SUPPORT"] = False  # Requires pre-release Eigen 3.4.90
        tc.cache_variables["BUILD_PYTHON_BINDINGS_WITH_BOOST_MPFR_SUPPORT"] = self.options.get_safe("with_mpfr", False)
        # Misc
        tc.cache_variables["JRL_CMAKE_MODULES"] = self.dependencies.build["jrl-cmakemodules"].cpp_info.builddirs[0].replace("\\", "/")
        tc.cache_variables["cppad_LIBRARY"] = "cppad::cppad"
        tc.cache_variables["cppadcg_LIBRARY"] = "cppadcg::cppadcg"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("coal", "cmake_file_name", "hpp-fcl")
        deps.set_property("cppadcodegen", "cmake_file_name", "cppadcg")
        deps.set_property("cppadcodegen", "cmake_target_name", "cppadcg::cppadcg")
        deps.set_property("qhull::libqhull_r", "cmake_target_name", "Qhull::qhull_r")
        deps.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        if self.options.get_safe("generate_python_stubs"):
            venv = self._utils.PythonVenv(self)
            venv.generate()
            # stubgen tries to load the built Python module
            if can_run(self):
                venv = VirtualRunEnv(self)
                venv.generate(scope="build")

    def _patch_sources(self):
        if not self.options.enable_template_instantiation:
            # Work around a bug in the CMake setup - no sources are added to these targets
            # when the template instantiation is disabled, so they need to be used with INTERFACE visibility.
            src_cmakelists = os.path.join(self.source_folder, "src", "CMakeLists.txt")
            replace_in_file(self, src_cmakelists, "pinocchio_default PUBLIC", "pinocchio_default INTERFACE")
            replace_in_file(self, src_cmakelists, "${PROJECT_NAME}_cppad PUBLIC", "${PROJECT_NAME}_cppad INTERFACE")
            replace_in_file(self, src_cmakelists, "${PROJECT_NAME}_cppadcg PUBLIC", "${PROJECT_NAME}_cppadcg INTERFACE")
            replace_in_file(self, src_cmakelists, "PUBLIC PINOCCHIO_WITH_HPP_FCL", "INTERFACE PINOCCHIO_WITH_HPP_FCL")
            replace_in_file(self, src_cmakelists, "PRIVATE COAL_DISABLE_HPP_FCL_WARNINGS", "INTERFACE COAL_DISABLE_HPP_FCL_WARNINGS")

    def build(self):
        if self.options.get_safe("generate_python_stubs"):
            self._utils.pip_install(self, ["scipy"])
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        # Compilation with EigenPy has a very high memory footprint, so limit the max number of jobs
        if self.options.python_bindings:
            self._utils.limit_build_jobs(self, gb_mem_per_job=2.5)
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def _find_installed_site_packages(self):
        return str(next(Path(self.package_folder).rglob("robot_wrapper.py")).parent.parent)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "pinocchio")
        self.cpp_info.set_property("cmake_config_version_compat", "AnyNewerVersion")
        self.cpp_info.set_property("pkg_config_name", "pinocchio")

        pinocchio = self.cpp_info.components["pinocchio_"]
        pinocchio.set_property("cmake_target_name", "pinocchio::pinocchio")
        pinocchio.requires = ["pinocchio_headers", "pinocchio_visualizers"]
        if self.options.with_qhull:
            pinocchio.requires.append("pinocchio_extra")

        headers = self.cpp_info.components["pinocchio_headers"]
        headers.set_property("cmake_target_name", "pinocchio::pinocchio_headers")
        headers.set_property("cmake_target_aliases", ["pinocchio::pinocchio_default"])
        headers.includedirs = ["include"]
        headers.requires = ["eigen::eigen", "boost::headers", "boost::serialization"]
        headers.defines = ["BOOST_MPL_LIMIT_LIST_SIZE=30", "BOOST_MPL_LIMIT_VECTOR_SIZE=30"]

        visualizers = self.cpp_info.components["pinocchio_visualizers"]
        visualizers.set_property("cmake_target_name", "pinocchio::pinocchio_visualizers")
        visualizers.libs = ["pinocchio_visualizers"]
        visualizers.requires = ["pinocchio_headers"]

        if self.options.with_coal:
            collision = self.cpp_info.components["pinocchio_collision"]
            collision.set_property("cmake_target_name", "pinocchio::pinocchio_collision")
            collision.libs = ["pinocchio_collision"]
            collision.requires = ["pinocchio_headers", "coal::coal"]
            collision.defines = ["PINOCCHIO_WITH_HPP_FCL"]
            pinocchio.requires.append("pinocchio_collision")

            if self.options.with_openmp:
                collision_parallel = self.cpp_info.components["pinocchio_collision_parallel"]
                collision_parallel.set_property("cmake_target_name", "pinocchio::pinocchio_collision_parallel")
                collision_parallel.requires = ["pinocchio_headers", "pinocchio_collision", "openmp::openmp"]
                pinocchio.requires.append("pinocchio_collision_parallel")

        if self.options.with_urdfdom:
            parsers = self.cpp_info.components["pinocchio_parsers"]
            parsers.set_property("cmake_target_name", "pinocchio::pinocchio_parsers")
            parsers.libs = ["pinocchio_parsers"]
            parsers.requires = ["pinocchio_headers", "boost::filesystem"]
            parsers.requires.append("urdfdom::urdfdom")
            parsers.defines = ["PINOCCHIO_WITH_URDFDOM"]
            pinocchio.requires.append("pinocchio_parsers")

        if self.options.with_openmp:
            parallel = self.cpp_info.components["pinocchio_parallel"]
            parallel.set_property("cmake_target_name", "pinocchio::pinocchio_parallel")
            parallel.requires = ["pinocchio_headers", "openmp::openmp"]
            pinocchio.requires.append("pinocchio_parallel")

        if self.options.with_cppad:
            cppad = self.cpp_info.components["pinocchio_cppad"]
            cppad.set_property("cmake_target_name", "pinocchio::pinocchio_cppad")
            cppad.requires = ["pinocchio_headers", "cppad::cppad"]
            cppad.defines = ["CPPAD_DEBUG_AND_RELEASE"]
            pinocchio.requires.append("pinocchio_cppad")

        if self.options.get_safe("with_codegen"):
            cppadcg = self.cpp_info.components["pinocchio_cppadcg"]
            cppadcg.set_property("cmake_target_name", "pinocchio::pinocchio_cppadcg")
            cppadcg.requires = ["pinocchio_headers", "cppad::cppad", "cppadcodegen::cppadcodegen"]
            cppadcg.defines = ["CPPAD_DEBUG_AND_RELEASE"]
            pinocchio.requires.append("pinocchio_cppadcg")

        if self.options.with_casadi:
            casadi = self.cpp_info.components["pinocchio_casadi"]
            casadi.set_property("cmake_target_name", "pinocchio::pinocchio_casadi")
            casadi.requires = ["pinocchio_headers", "casadi::casadi"]
            pinocchio.requires.append("pinocchio_casadi")

        if self.options.with_qhull:
            extra = self.cpp_info.components["pinocchio_extra"]
            extra.set_property("cmake_target_name", "pinocchio::pinocchio_extra")
            extra.libs = ["pinocchio_extra"]
            extra.requires = ["pinocchio_headers", "qhull::qhull"]
            extra.defines = ["PINOCCHIO_WITH_EXTRA_SUPPORT"]
            pinocchio.requires.append("pinocchio_extra")

        if self.options.build_python_parser:
            python_parser = self.cpp_info.components["pinocchio_python_parser"]
            python_parser.set_property("cmake_target_name", "pinocchio::pinocchio_python_parser")
            python_parser.libs = ["pinocchio_python_parser"]
            python_parser.requires = ["pinocchio_headers", "cpython::cpython"]
            if self.options.with_coal:
                python_parser.requires.append("pinocchio_collision")
            pinocchio.requires.append("pinocchio_python_parser")

        if self.options.python_bindings:
            self.cpp_info.components["_bindings"].requires = ["eigenpy::eigenpy"]
            if self.options.with_mpfr:
                self.cpp_info.components["_bindings"].requires.extend(["gmp::gmp", "mpfr::mpfr"])
            self.runenv_info.prepend_path("PYTHONPATH", self._find_installed_site_packages())
