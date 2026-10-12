import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout, CMakeDeps
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class SundialsConan(ConanFile):
    name = "sundials"
    license = "BSD-3-Clause"
    description = ("SUNDIALS is a family of software packages implemented with the goal of providing robust time integrators"
                   " and nonlinear solvers that can easily be incorporated into existing simulation codes.")
    topics = ("integrators", "ode", "non-linear-solvers")
    homepage = "https://github.com/LLNL/sundials"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_arkode": [True, False],
        "build_cvode": [True, False],
        "build_cvodes": [True, False],
        "build_ida": [True, False],
        "build_idas": [True, False],
        "build_kinsol": [True, False],
        "with_cuda": [True, False],
        "with_ginkgo": [True, False],
        "with_klu": [True, False],
        "with_lapack": [True, False],
        "with_mpi": [True, False],
        "with_openmp": [True, False],
        "with_superlumt": [True, False],
        "index_size": [32, 64],
        "precision": ["single", "double", "extended"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_arkode": True,
        "build_cvode": True,
        "build_cvodes": True,
        "build_ida": True,
        "build_idas": True,
        "build_kinsol": True,
        "with_cuda": False,
        "with_ginkgo": False,
        "with_klu": True,
        "with_lapack": True,
        "with_mpi": False,
        "with_openmp": True,
        "with_superlumt": True,
        "index_size": 64,
        "precision": "double",
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if Version(self.version) < "6.0":
            del self.options.with_ginkgo
            self.options.with_cuda.value = False
        if not self.options.with_cuda:
            del self.settings.cuda
        if not self.options.with_cuda and not self.options.with_mpi:
            self.languages = ["C"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Used in public headers:
        # - caliper: sundials/sundials_profiler.h
        # - cuda: sunmemory/sunmemory_cuda.h, nvector/nvector_cuda.h
        # - ginkgo: sunmatrix/sunmatrix_ginkgo.hpp, sunlinsol/sunlinsol_ginkgo.hpp
        # - klu: sunlinsol/sunlinsol_klu.h
        # - mpi: sundials/sundials_types.h, sundials/priv/sundials_mpi_errors_impl.h
        if self.options.get_safe("with_ginkgo"):
            self.requires("ginkgo/[^1.8]", transitive_headers=True, transitive_libs=True)
        if self.options.with_klu:
            self.requires("suitesparse-klu/[^2.3.5]", transitive_headers=True, transitive_libs=True)
        if self.options.with_lapack:
            self.requires("lapack/latest")
        if self.options.with_mpi:
            self.requires("openmpi/[>=4.1.6 <6]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openmp:
            self.requires("openmp/system")
        if self.options.with_superlumt:
            self.requires("superlu_mt/[^4.0.1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_cuda:
            self.cuda.requires("cudart")
            if self.options.index_size == 32:
                self.cuda.requires("cusparse")
                self.cuda.requires("cusolver")

    def validate(self):
        if self.options.with_klu and self.options.precision != "double":
            # https://github.com/LLNL/sundials/blob/v7.1.1/cmake/tpl/SundialsKLU.cmake#L40
            raise ConanInvalidConfiguration("-o sundials/*:with_klu=True is only compatible with -o sundials/*:precision=double")
        if self.options.precision == "extended":
            # https://github.com/LLNL/sundials/blob/v7.1.1/cmake/tpl/SundialsGinkgo.cmake#L57
            # https://github.com/LLNL/sundials/blob/v7.1.1/cmake/tpl/SundialsLapack.cmake#L40
            for opt in ["with_cuda", "with_ginkgo", "with_lapack"]:
                if self.options.get_safe(opt):
                    raise ConanInvalidConfiguration(f"-o sundials/*:{opt}=True is not compatible with -o sundials/*:precision=extended")
        if self.options.with_cuda:
            self.cuda.validate_settings()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18 <5]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        save(self, "examples/CMakeLists.txt", "")
        if Version(self.version) < "3.0":
            replace_in_file(self, "CMakeLists.txt", "CMAKE_MINIMUM_REQUIRED(VERSION 2.8.1)", "CMAKE_MINIMUM_REQUIRED(VERSION 3.5)")
            save(self, "config/SundialsLapack.cmake", "find_package(LAPACK REQUIRED)")
            save(self, "config/SundialsFortran.cmake", "")
            save(self, "config/SundialsFortran90.cmake", "")
            save(self, "config/SundialsSuperLUMT.cmake", "find_package(SUPERLUMT REQUIRED)")
            save(self, "config/SundialsKLU.cmake", "find_package(KLU REQUIRED)")
            save(self, "config/SundialsMPIC.cmake", textwrap.dedent("""\
                find_package(MPI REQUIRED CONFIG)
                get_target_property(MPI_INCLUDE_PATH MPI::MPI_C INTERFACE_INCLUDE_DIRECTORIES)
                set(MPIC_FOUND TRUE)
                set(MPIC_MPI2 TRUE)
                """))
            save(self, "config/SundialsMPICXX.cmake", "")
            save(self, "config/SundialsMPIF.cmake", "")
            save(self, "config/SundialsMPIF90.cmake", "")
            replace_in_file(self, "CMakeLists.txt", "INCLUDE_DIRECTORIES(${KLU_INCLUDE_DIR})", "link_libraries(SUNDIALS::KLU)")

    @property
    def _ginkgo_backends(self):
        if not self.options.get_safe("with_ginkgo"):
            return []
        backends = ["REF"]
        if self.dependencies["ginkgo"].options.cuda:
            backends.append("CUDA")
        if self.dependencies["ginkgo"].options.openmp:
            backends.append("OMP")
        return backends

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_Fortran_COMPILER"] = ""
        if Version(self.version) >= "7.7":
            tc.cache_variables["SUNDIALS_ENABLE_C_EXAMPLES"] = False
            tc.cache_variables["SUNDIALS_ENABLE_CXX_EXAMPLES"] = False
            tc.cache_variables["SUNDIALS_ENABLE_EXAMPLES_INSTALL"] = False
            tc.cache_variables["SUNDIALS_ENABLE_BENCHMARKS"] = False
        else:
            tc.cache_variables["EXAMPLES_ENABLE_C"] = False
            tc.cache_variables["EXAMPLES_ENABLE_CXX"] = False
            tc.cache_variables["EXAMPLES_INSTALL"] = False
            tc.cache_variables["BUILD_BENCHMARKS"] = False
        test_option = "SUNDIALS_TEST_ENABLE_UNIT_TESTS" if Version(self.version) >= "7.4" else "SUNDIALS_TEST_UNITTESTS"
        tc.cache_variables[test_option] = False
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)

        # https://github.com/LLNL/sundials/blob/v7.1.1/cmake/SundialsBuildOptionsPre.cmake
        tc.cache_variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["SUNDIALS_INDEX_SIZE"] = self.options.index_size
        tc.cache_variables["SUNDIALS_PRECISION"] = str(self.options.precision).upper()
        if Version(self.version) >= "7.7":
            tc.cache_variables["SUNDIALS_ENABLE_ARKODE"] = self.options.build_arkode
            tc.cache_variables["SUNDIALS_ENABLE_CVODE"] = self.options.build_cvode
            tc.cache_variables["SUNDIALS_ENABLE_CVODES"] = self.options.build_cvodes
            tc.cache_variables["SUNDIALS_ENABLE_IDA"] = self.options.build_ida
            tc.cache_variables["SUNDIALS_ENABLE_IDAS"] = self.options.build_idas
            tc.cache_variables["SUNDIALS_ENABLE_KINSOL"] = self.options.build_kinsol
            tc.cache_variables["SUNDIALS_ENABLE_FORTRAN"] = False
            tc.cache_variables["SUNDIALS_ENABLE_PYTHON"] = False
            tc.cache_variables["SUNDIALS_ENABLE_MONITORING"] = False
            tc.cache_variables["SUNDIALS_ENABLE_PROFILING"] = False
        else:
            tc.cache_variables["BUILD_ARKODE"] = self.options.build_arkode
            tc.cache_variables["BUILD_CVODE"] = self.options.build_cvode
            tc.cache_variables["BUILD_CVODES"] = self.options.build_cvodes
            tc.cache_variables["BUILD_IDA"] = self.options.build_ida
            tc.cache_variables["BUILD_IDAS"] = self.options.build_idas
            tc.cache_variables["BUILD_KINSOL"] = self.options.build_kinsol

        # https://github.com/LLNL/sundials/blob/v7.1.1/cmake/SundialsTPLOptions.cmake
        tpl_prefix = "SUNDIALS_" if Version(self.version) >= "7.7" else ""
        tc.cache_variables[f"{tpl_prefix}ENABLE_MPI"] = self.options.with_mpi
        tc.cache_variables[f"{tpl_prefix}ENABLE_OPENMP"] = self.options.with_openmp
        tc.cache_variables[f"{tpl_prefix}ENABLE_OPENMP_DEVICE"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_PTHREAD"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_CUDA"] = self.options.with_cuda
        tc.cache_variables[f"{tpl_prefix}ENABLE_HIP"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_SYCL"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_LAPACK"] = self.options.with_lapack
        tc.cache_variables[f"{tpl_prefix}ENABLE_GINKGO"] = self.options.get_safe("with_ginkgo", False)
        if self.options.get_safe("with_ginkgo"):
            tc.cache_variables["SUNDIALS_GINKGO_BACKENDS"] = ";".join(self._ginkgo_backends)
        tc.cache_variables[f"{tpl_prefix}ENABLE_MAGMA"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_SUPERLUDIST"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_SUPERLUMT"] = self.options.with_superlumt
        tc.cache_variables[f"{tpl_prefix}ENABLE_KLU"] = self.options.with_klu
        tc.cache_variables[f"{tpl_prefix}ENABLE_HYPRE"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_PETSC"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_RAJA"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_TRILINOS"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_XBRAID"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_ONEMKL"] = False
        tc.cache_variables[f"{tpl_prefix}ENABLE_KOKKOS"] = False
        if Version(self.version) >= "7.7":
            tc.cache_variables["SUNDIALS_ENABLE_LAPACK_CHECKS"] = False
            tc.cache_variables["SUNDIALS_ENABLE_GINKGO_CHECKS"] = False
            tc.cache_variables["SUNDIALS_ENABLE_SUPERLUMT_CHECKS"] = False
            tc.cache_variables["SUNDIALS_ENABLE_KLU_CHECKS"] = False
        else:
            tc.cache_variables["LAPACK_WORKS"] = True
            tc.cache_variables["GINKGO_WORKS"] = True
            tc.cache_variables["SUPERLUMT_WORKS"] = True
            tc.cache_variables["KLU_WORKS"] = True

        # https://github.com/LLNL/sundials/blob/v7.1.1/cmake/SundialsBuildOptionsPost.cmake
        module_prefix = "SUNDIALS_ENABLE_" if Version(self.version) >= "7.7" else "BUILD_"
        if Version(self.version) < "7.7" or self.options.get_safe("with_cuda"):
            tc.cache_variables[f"{module_prefix}SUNMATRIX_CUSPARSE"] = self.options.get_safe("with_cuda", False) and self.options.index_size == 32
            tc.cache_variables[f"{module_prefix}SUNLINSOL_CUSOLVERSP"] = self.options.get_safe("with_cuda", False) and self.options.index_size == 32

        # Configure default LAPACK naming conventions for OpenBLAS.
        # Needed to avoid a Fortran compiler requirement to detect the correct name mangling scheme.
        # https://github.com/LLNL/sundials/blob/v7.1.1/cmake/SundialsSetupCompilers.cmake#L269-L360
        tc.cache_variables["SUNDIALS_LAPACK_CASE"] = "lower"
        tc.cache_variables["SUNDIALS_LAPACK_UNDERSCORES"] = "one"

        if self.options.with_cuda:
            tc.cache_variables["CMAKE_CUDA_ARCHITECTURES"] = str(self.settings.cuda.architectures).replace(",", ";")

        if Version(self.version) < "3.0":
            tc.cache_variables["LAPACK_ENABLE"] = self.options.with_lapack
            tc.cache_variables["SUPERLUMT_ENABLE"] = self.options.with_superlumt
            tc.cache_variables["KLU_ENABLE"] = self.options.with_klu
            tc.cache_variables["MPI_ENABLE"] = self.options.with_mpi
            tc.cache_variables["OPENMP_ENABLE"] = self.options.with_openmp
            tc.cache_variables["PTHREAD_ENABLE"] = False
            tc.cache_variables["HYPRE_ENABLE"] = False
            tc.cache_variables["PETSC_ENABLE"] = False
            tc.cache_variables["EXAMPLES_ENABLE"] = False

        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("suitesparse-klu", "cmake_target_name", "SUNDIALS::KLU")
        deps.set_property("superlu_mt", "cmake_file_name", "SUPERLUMT")
        deps.set_property("superlu_mt", "cmake_target_name", "SUNDIALS::SUPERLUMT")
        if self.options.get_safe("with_ginkgo"):
            ginkgo = self.dependencies["ginkgo"]
            deps.set_property("ginkgo", "cmake_extra_variables", {
                "GINKGO_PROJECT_VERSION": str(ginkgo.ref.version),
                "GINKGO_BUILD_REFERENCE": True,
                "GINKGO_BUILD_OMP": bool(ginkgo.options.openmp),
                "GINKGO_BUILD_CUDA": bool(ginkgo.options.cuda),
                "GINKGO_BUILD_HIP": False,
                "GINKGO_BUILD_SYCL": False,
            })
        if self.options.with_mpi:
            deps.set_property("openmpi", "cmake_extra_variables", {
                "MPI_C_FOUND": 1,
                "MPI_INCLUDE_PATH": "${MPI_INCLUDE_DIRS}",
            })
        deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def _patch_sources(self):
        if self.options.get_safe("with_ginkgo") and Version(self.version) < "7.9":
            replace_in_file(self, os.path.join(self.source_folder, "cmake", "tpl", "SundialsGinkgo.cmake"),
                            "NO_DEFAULT_PATH", "")
        if self.options.with_mpi and Version(self.version) >= "3.0":
            replace_in_file(self, os.path.join(self.source_folder, "cmake", "tpl", "SundialsMPI.cmake"),
                            "find_package(MPI 2.0.0 REQUIRED)", "find_package(MPI REQUIRED)")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "Windows" and self.options.shared:
            mkdir(self, os.path.join(self.package_folder, "bin"))
            for dll_path in glob.glob(os.path.join(self.package_folder, "lib", "*.dll")):
                shutil.move(dll_path, os.path.join(self.package_folder, "bin", os.path.basename(dll_path)))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        fix_apple_shared_install_name(self)
        if Version(self.version) < "3.0":
            # For CasADi
            shutil.copy(os.path.join(self.source_folder, "src/kinsol/kinsol_spils_impl.h"),
                        os.path.join(self.package_folder, "include/kinsol/kinsol_spils_impl.h"))

    def package_info(self):
        # https://github.com/LLNL/sundials/blob/v7.1.1/cmake/SUNDIALSConfig.cmake.in
        if Version(self.version) >= "5.8.0":
            self.cpp_info.set_property("cmake_file_name", "SUNDIALS")

        suffix = ""
        if Version(self.version) >= "7.0" and self.settings.os == "Windows":
            suffix = "_shared" if self.options.shared else "_static"

        core_lib = None
        if Version(self.version) >= "7.0":
            core_lib = "core"
        elif Version(self.version) >= "5.8.0":
            core_lib = "generic"

        def _add_lib(name, requires=None, system_libs=None, interface=False):
            if Version(self.version) >= "5.8.0":
                component = self.cpp_info.components[name]
                component.set_property("cmake_target_name", f"SUNDIALS::{name}")
                component.set_property("cmake_target_aliases", [f"SUNDIALS::{name}_{'shared' if self.options.shared else 'static'}"])
            else:
                # For backward compatibility with old recipe versions
                component = self.cpp_info.components[f"sundials_{name}"]
                requires = [f"sundials_{r}" if "::" not in r else r for r in requires or []]
            if not interface:
                component.libs = [f"sundials_{name}{suffix}"]
                if Version(self.version) >= "7.0" and not self.options.shared:
                    component.defines = ["SUNDIALS_STATIC_DEFINE"]
            component.requires = requires or []
            component.system_libs = system_libs or []
            if core_lib and name != core_lib:
                component.requires.append(core_lib)
            if self.settings.os in ["Linux", "FreeBSD"]:
                component.system_libs.append("m")

        core_requires_mpi = core_lib == "core" and self.options.with_mpi
        if core_lib:
            _add_lib(core_lib, requires=["openmpi::ompi-c"] if core_requires_mpi else None)

        if self.options.build_arkode:
            _add_lib("arkode")
        if self.options.build_cvode:
            _add_lib("cvode")
        if self.options.build_cvodes:
            _add_lib("cvodes")
        if self.options.build_ida:
            _add_lib("ida")
        if self.options.build_idas:
            _add_lib("idas")
        if self.options.build_kinsol:
            _add_lib("kinsol")

        _add_lib("nvecserial")
        if Version(self.version) >= "5.8.0":
            _add_lib("nvecmanyvector")
        if self.options.with_mpi:
            mpi_requires = [] if core_requires_mpi else ["openmpi::ompi-c"]
            _add_lib("nvecparallel", requires=mpi_requires)
            if Version(self.version) >= "5.8.0":
                _add_lib("nvecmpimanyvector", requires=mpi_requires)
                _add_lib("nvecmpiplusx", requires=mpi_requires)
        if self.options.with_openmp:
            _add_lib("nvecopenmp", requires=["openmp::openmp"])

        if Version(self.version) < "3.0":
            for _, component in self.cpp_info.components.items():
                if self.options.with_klu:
                    component.requires.append("suitesparse-klu::suitesparse-klu")
                if self.options.with_lapack:
                    component.requires.append("lapack::lapack")
                if self.options.with_superlumt:
                    component.requires.append("superlu_mt::superlu_mt")
            return

        _add_lib("sunmatrixband")
        _add_lib("sunmatrixdense")
        _add_lib("sunmatrixsparse")
        if self.options.get_safe("with_ginkgo"):
            _add_lib("sunmatrixginkgo", interface=True, requires=["ginkgo::ginkgo"])

        _add_lib("sunlinsolband", requires=["sunmatrixband"])
        _add_lib("sunlinsoldense", requires=["sunmatrixdense"])
        _add_lib("sunlinsolpcg")
        _add_lib("sunlinsolspbcgs")
        _add_lib("sunlinsolspfgmr")
        _add_lib("sunlinsolspgmr")
        _add_lib("sunlinsolsptfqmr")
        if self.options.get_safe("with_ginkgo"):
            _add_lib("sunmatrixginkgo", interface=True, requires=["ginkgo::ginkgo"])
            _add_lib("sunlinsolginkgo", interface=True, requires=["ginkgo::ginkgo"])
        if self.options.with_klu:
            _add_lib("sunlinsolklu", requires=["sunmatrixsparse", "suitesparse-klu::suitesparse-klu"])
        if self.options.with_lapack:
            _add_lib("sunlinsollapackband", requires=["sunmatrixband", "lapack::lapack"])
            _add_lib("sunlinsollapackdense", requires=["sunmatrixdense", "lapack::lapack"])
        if self.options.with_superlumt:
            _add_lib("sunlinsolsuperlumt", requires=["sunmatrixsparse", "superlu_mt::superlu_mt"])

        _add_lib("sunnonlinsolfixedpoint")
        _add_lib("sunnonlinsolnewton")
        if Version(self.version) >= "7.8":
            _add_lib("sunnonlinsolauto", requires=["sunnonlinsolfixedpoint", "sunnonlinsolnewton"])

        if Version(self.version) >= "7.5":
            _add_lib("sundomeigestpower")
            if self.options.with_lapack:
                _add_lib("sundomeigestarnoldi", requires=["lapack::lapack"])

        if self.options.with_cuda:
            _add_lib("nveccuda", requires=["cudart::cudart_"])
            if self.options.index_size == 32:
                _add_lib("sunmatrixcusparse", requires=["cusparse::cusparse"])
                _add_lib("sunlinsolcusolversp", requires=["sunmatrixcusparse", "cusolver::cusolver_"])
