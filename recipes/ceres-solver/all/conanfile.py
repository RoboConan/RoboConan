import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class CeresSolverConan(ConanFile):
    name = "ceres-solver"
    description = "Ceres Solver is an open source C++ library for modeling and solving large, complicated optimization problems."
    license = "BSD-3-Clause"
    homepage = "http://ceres-solver.org/"
    topics = ("optimization", "non-linear least squares")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "use_cuda": [True, False],
        "use_eigen_metis": [True, False],
        "use_lapack": [True, False],
        "use_eigen_sparse": [True, False],
        "use_suitesparse": [True, False],
        "use_accelerate": [True, False],
        "use_custom_blas": [True, False],
        "use_schur_specializations": [True, False],
        # Unavailable since v2.0.0
        "use_CXX11": [True, False],
        "use_CXX11_threads": [True, False],
        "use_OpenMP": [True, False],
        "use_TBB": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "use_cuda": False,
        "use_eigen_metis": True,
        "use_lapack": True,
        "use_eigen_sparse": True,  # uses LGPL-licensed parts of Eigen
        "use_suitesparse": True,
        "use_accelerate": True,
        "use_custom_blas": True,
        "use_schur_specializations": True,
        "use_CXX11": False,
        "use_CXX11_threads": False,
        "use_OpenMP": True,
        "use_TBB": False,

        "eigen/*:MPL2_only": False,
    }
    options_description = {
        "use_cuda": "Enable CUDA support.",
        "use_lapack": "Enable use of LAPACK directly within Ceres.",
        "use_eigen_sparse": "Enable Eigen as a sparse linear algebra library.",
        "use_suitesparse": "Enable SuiteSparse support.",
        "use_accelerate": "Enable use of sparse solvers in Apple's Accelerate framework.",
        "use_custom_blas": "Use handcoded BLAS routines (usually faster) instead of Eigen.",
        "use_schur_specializations": ("Enable template specializations for the fixed-size Schur complement based solvers. "
                                      "Can impact compilation time and memory usage and binary size."),
    }

    python_requires = ["conan-cuda/latest", "conan-utils/latest"]
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    @property
    def _min_cppstd(self):
        if Version(self.version) >= "2.2.0":
            return 17
        if Version(self.version) >= "2.0.0":
            return 14
        return 98

    @property
    def _use_miniglog(self):
        # https://github.com/ceres-solver/ceres-solver/blob/2.2.0/CMakeLists.txt#L168-L175
        return Version(self.version, qualifier=True) < "2.3.0" and self.settings.os == "iOS"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "FindSuiteSparse.cmake", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if Version(self.version) >= "2.0":
            del self.options.use_TBB
            del self.options.use_OpenMP
            del self.options.use_CXX11_threads
            del self.options.use_CXX11
        if Version(self.version) < "2.2.0":
            del self.options.use_eigen_metis
        if Version(self.version) < "2.1.0":
            del self.options.use_cuda

        if not is_apple_os(self) or self.version < "2.0.0":
            del self.options.use_accelerate

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.get_safe("use_eigen_metis"):
            self.options.use_eigen_sparse.value = True
        if not self.options.get_safe("use_cuda"):
            del self.settings.cuda
        # https://github.com/ceres-solver/ceres-solver/blob/2.2.0/CMakeLists.txt#L168-L175
        if self.settings.os == "iOS":
            self.options.use_lapack.value = False
            self.options.use_suitesparse.value = False

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _require_metis(self):
        if Version(self.version) < "2.2.0":
            return False
        return self.options.get_safe("use_eigen_metis") or self.options.use_suitesparse

    def requirements(self):
        if Version(self.version) >= "2.0":
            self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        else:
            self.requires("eigen/[^3.3]", transitive_headers=True)
        if Version(self.version, qualifier=True) >= "2.3.0":
            self.requires("abseil/[>=20240116]", transitive_headers=True, transitive_libs=True)
        elif not self._use_miniglog:
            self.requires("glog/0.6.0", transitive_headers=True, transitive_libs=True)
        if self.options.use_suitesparse:
            self.requires("suitesparse-spqr/[^4.3.4]")
            self.requires("suitesparse-cholmod/[^5.3.0]")
            if Version(self.version) < "2.2.0":
                self.requires("suitesparse-cxsparse/[^4.4.1]")
        if self.options.use_lapack:
            self.requires("lapack/latest")
        if self._require_metis:
            self.requires("metis/5.2.1")
        if self.options.get_safe("use_TBB"):
            self.requires("onetbb/[^2020.3]")
        if self.options.get_safe("use_OpenMP"):
            self.requires("openmp/system")
        if self.options.get_safe("use_cuda"):
            self.cuda.requires("cudart")
            self.cuda.requires("cublas")
            self.cuda.requires("cusparse")
            self.cuda.requires("cusolver")
            if Version(self.version, qualifier=True) >= "2.3.0":
                self.cuda.requires("cudss")

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)
        if self.options.get_safe("use_cuda"):
            self.cuda.validate_settings()
        # https://github.com/ceres-solver/ceres-solver/blob/2.2.0/CMakeLists.txt#L203
        if self.options.use_eigen_sparse:
            if self.dependencies["eigen"].ref.version < 5 and self.dependencies["eigen"].options.MPL2_only:
                raise ConanInvalidConfiguration("use_eigen_sparse=True requires eigen with MPL2_only=False")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18]")
        if Version(self.version) >= "2.2.0" and self.options.use_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        if Version(self.version) < "2.0":
            replace_in_file(self, "CMakeLists.txt", "cmake_minimum_required(VERSION 2.8.0)", "cmake_minimum_required(VERSION 3.5)")
            replace_in_file(self, "CMakeLists.txt", "cmake_policy(VERSION 2.8)", "")
        elif Version(self.version) <= "2.2.0":
            replace_in_file(self, "CMakeLists.txt", "Eigen3 3.3 ", "Eigen3 ")
        else:
            replace_in_file(self, "CMakeLists.txt", "Eigen3 3.3.4...5 ", "Eigen3 ")
        copy(self, "FindSuiteSparse.cmake", self.export_sources_folder, os.path.join(self.source_folder, "cmake"))
        if Version(self.version) >= "2.2.0":
            # Don't force CMAKE_CUDA_ARCHITECTURES, let CudaToolchain handle it
            replace_in_file(self, "CMakeLists.txt",
                            "CMAKE_CUDA_ARCHITECTURES",
                            "CMAKE_CUDA_ARCHITECTURES_ignored")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_DOCUMENTATION"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["PROVIDE_UNINSTALL_TARGET"] = False

        tc.variables["CUSTOM_BLAS"] = self.options.use_custom_blas
        tc.variables["EIGENSPARSE"] = self.options.use_eigen_sparse
        if Version(self.version, qualifier=True) < "2.3.0":
            tc.variables["GFLAGS"] = False # useless for the lib itself, gflags is not a direct dependency
        tc.variables["LAPACK"] = self.options.use_lapack
        tc.variables["MINIGLOG"] = self._use_miniglog
        tc.variables["SCHUR_SPECIALIZATIONS"] = self.options.use_schur_specializations
        tc.variables["SUITESPARSE"] = self.options.use_suitesparse
        if self.options.use_suitesparse:
            tc.variables["SuiteSparse_VERSION"] = str(self.dependencies["suitesparse-config"].ref.version)
            tc.variables["SuiteSparse_Partition_FOUND"] = self.dependencies["suitesparse-cholmod"].options.build_partition

        # IOS_DEPLOYMENT_TARGET variable was added to iOS.cmake file in 1.12.0 version
        if self.settings.os == "iOS":
            tc.variables["IOS_DEPLOYMENT_TARGET"] = self.settings.os.version

        ceres_version = Version(self.version)
        if ceres_version >= "2.2.0":
            tc.variables["USE_CUDA"] = self.options.get_safe("use_cuda", False)
        elif ceres_version >= "2.1.0":
            tc.variables["CUDA"] = self.options.get_safe("use_cuda", False)
        if ceres_version >= "2.2.0":
            tc.variables["EIGENMETIS"] = self.options.use_eigen_metis
        if ceres_version >= "2.0.0":
            tc.variables["ACCELERATESPARSE"] = self.options.get_safe("use_accelerate", False)

        if ceres_version < "2.2.0":
            tc.variables["CXSPARSE"] = self.options.get_safe("use_suitesparse", False)
            tc.variables["MSVC_USE_STATIC_CRT"] = is_msvc_static_runtime(self)
            tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        if ceres_version < "2.1.0":
            tc.variables["LIB_SUFFIX"] = ""
        if ceres_version < "2.0.0":
            tc.variables["CXX11"] = self.options.use_CXX11
            tc.variables["OPENMP"] = self.options.use_OpenMP
            tc.variables["TBB"] = self.options.use_TBB
            tc.variables["CXX11_THREADS"] = self.options.use_CXX11_threads
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("metis", "cmake_file_name", "METIS")
        deps.set_property("metis", "cmake_target_name", "METIS::METIS")
        deps.set_property("suitesparse-cxsparse", "cmake_target_name", "CXSparse::CXSparse")
        deps.generate()

        if Version(self.version) >= "2.2.0" and self.options.use_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self._utils.limit_build_jobs(self, gb_mem_per_job=1)
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "CMake"))
        self._create_cmake_module_variables(os.path.join(self.package_folder, self._module_variables_file_rel_path))

    def _create_cmake_module_variables(self, module_file):
        # Define several variables of upstream CMake config file which are not
        # defined out of the box by CMakeDeps.
        # See https://github.com/ceres-solver/ceres-solver/blob/master/cmake/CeresConfig.cmake.in
        content = textwrap.dedent(f"""\
            set(CERES_FOUND TRUE)
            set(CERES_VERSION {self.version})
            if(NOT DEFINED CERES_LIBRARIES)
                set(CERES_LIBRARIES Ceres::ceres)
            endif()
        """)
        save(self, module_file, content)

    @property
    def _module_variables_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-variables.cmake")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Ceres")

        libsuffix = "-debug" if self.settings.build_type == "Debug" else ""
        self.cpp_info.components["ceres"].set_property("cmake_target_name", "Ceres::ceres")
        # see https://github.com/ceres-solver/ceres-solver/blob/2.2.0/cmake/CeresConfig.cmake.in#L334-L340
        self.cpp_info.components["ceres"].set_property("cmake_target_aliases", ["ceres"])
        self.cpp_info.components["ceres"].libs = [f"ceres{libsuffix}"]
        if self._use_miniglog:
            self.cpp_info.components["ceres"].includedirs.append("include/ceres/internal/miniglog")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["ceres"].system_libs = ["m", "pthread"]
        if self.options.get_safe("use_accelerate"):
            self.cpp_info.components["ceres"].frameworks = ["Accelerate"]

        requires = ["eigen::eigen"]
        if Version(self.version, qualifier=True) >= "2.3.0":
            # Based on https://github.com/ceres-solver/ceres-solver/blob/93e66f0/bazel/ceres.bzl#L215-L222
            requires.extend([
                "abseil::btree",
                "abseil::check",
                "abseil::fixed_array",
                "abseil::flat_hash_map",
                "abseil::flat_hash_set",
                "abseil::log",
                "abseil::strings",
                "abseil::time",
                "abseil::vlog_is_on",
            ])
        elif not self._use_miniglog:
            requires.append("glog::glog")
        if self.options.use_suitesparse:
            requires.append("suitesparse-cholmod::suitesparse-cholmod")
            requires.append("suitesparse-spqr::suitesparse-spqr")
            if Version(self.version) < "2.2.0":
                requires.append("suitesparse-cxsparse::suitesparse-cxsparse")
        if self.options.use_lapack:
            requires.append("lapack::lapack")
        if self._require_metis:
            requires.append("metis::metis")
        if self.options.get_safe("use_TBB"):
            requires.append("onetbb::onetbb")
        if self.options.get_safe("use_OpenMP"):
            requires.append("openmp::openmp")
        self.cpp_info.components["ceres"].requires = requires

        if not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.components["ceres"].system_libs.append(libcxx)

        if self.options.get_safe("use_cuda"):
            self.cpp_info.components["ceres"].requires.extend([
                "cudart::cudart_",
                "cublas::cublas_",
                "cusolver::cusolver_",
                "cusparse::cusparse",
            ])
            if Version(self.version, qualifier=True) >= "2.3.0":
                self.cpp_info.components["ceres"].requires.append("cudss::cudss_")
            if Version(self.version) >= "2.2.0":
                self.cpp_info.components["ceres_cuda_kernels"].set_property("cmake_target_name", "Ceres::ceres_cuda_kernels")
                self.cpp_info.components["ceres_cuda_kernels"].libs.append(f"ceres_cuda_kernels{libsuffix}")
                self.cpp_info.components["ceres_cuda_kernels"].requires = ["cudart::cudart_"]
                if not self.options.shared:
                    self.cpp_info.components["ceres"].requires.append("ceres_cuda_kernels")

        self.cpp_info.set_property("cmake_build_modules", [self._module_variables_file_rel_path])
