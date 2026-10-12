import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import check_min_vs, is_msvc, msvc_runtime_flag
from conan.tools.scm import Version

required_conan_version = ">=2.21"  # for cmake_extra_variables


class GtsamConan(ConanFile):
    name = "gtsam"
    license = "BSD-3-Clause"
    homepage = "https://github.com/borglab/gtsam"
    description = ("GTSAM is a library of C++ classes that implement "
                   "smoothing and mapping (SAM) in robotics and vision")
    topics = ("mapping", "smoothing", "optimization", "factor-graphs",
              "state-estimation", "computer-vision", "robotics")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "allow_deprecated": [True, False],
        "build_type_postfixes": [True, False],
        "build_unstable": [True, False],
        "build_with_march_native": [True, False],
        "default_allocator": [None, "STL", "BoostPool", "TBB", "tcmalloc"],
        "disable_new_timers": [True, False],
        "enable_boost_serialization": [True, False],
        "enable_consistency_checks": [True, False],
        "install_cppunitlite": [True, False],
        "install_matlab_toolbox": [True, False],
        "liegroup_preintegration": [True, False],
        "navstate_expmap": [True, False],
        "pose3_expmap": [True, False],
        "rot3_expmap": [True, False],
        "slow_but_correct_betweenfactor": [True, False],
        "support_nested_dissection": [True, False],
        "tangent_preintegration": [True, False],
        "throw_cheirality_exception": [True, False],
        "use_boost_features": [True, False],
        "use_quaternions": [True, False],
        "with_tbb": [True, False],
        "with_cholmod": [True, False],
        "with_cuda": [True, False],
        "with_cudss": [True, False],
        "with_mkl": [True, False],
        "with_mosek": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "allow_deprecated": True,
        "build_type_postfixes": True,
        "build_unstable": True,
        "build_with_march_native": False,
        "default_allocator": None,
        "disable_new_timers": False,
        "enable_boost_serialization": True,
        "enable_consistency_checks": False,
        "install_cppunitlite": False,
        "install_matlab_toolbox": False,
        "liegroup_preintegration": False,
        "navstate_expmap": False,
        "pose3_expmap": True,
        "rot3_expmap": True,
        "slow_but_correct_betweenfactor": True,
        "support_nested_dissection": True,
        "tangent_preintegration": True,
        "throw_cheirality_exception": True,
        "use_boost_features": True,
        "use_quaternions": False,
        "with_tbb": True,
        "with_cholmod": False,
        "with_cuda": False,
        "with_cudss": False,
        "with_mkl": False,
        "with_mosek": False,
    }
    options_description = {
        "allow_deprecated": "Allow use of deprecated methods/functions",
        "build_type_postfixes": "Append the build type to compiled library names",
        "build_unstable": "Enable building of gtsam_unstable",
        "build_with_march_native": "Build for the native architecture (binary may not be portable)",
        "default_allocator": "Select the preferred memory allocator",
        "disable_new_timers": "Disable Boost.chrono-based timers",
        "enable_boost_serialization": "Enable Boost serialization support",
        "enable_consistency_checks": "Enable expensive consistency checks",
        "install_cppunitlite": "Install CppUnitLite as a component",
        "install_matlab_toolbox": "Install the MATLAB toolbox",
        "liegroup_preintegration": "Use NavState SE_2(3) Lie-group IMU preintegration by default",
        "navstate_expmap": "Use the full NavState SE_2(3) Expmap/Logmap chart",
        "pose3_expmap": "Use Pose3::EXPMAP instead of Pose3::FIRST_ORDER",
        "rot3_expmap": "Use Rot3::EXPMAP when quaternion rotations are enabled",
        "slow_but_correct_betweenfactor": "Use local Jacobians in BetweenFactor and PriorFactor",
        "support_nested_dissection": "Support METIS-based nested dissection",
        "tangent_preintegration": "Use IMU integration on tangent space",
        "throw_cheirality_exception": "Throw when a triangulated point is behind a camera",
        "use_boost_features": "Enable GTSAM features implemented with Boost",
        "use_quaternions": "Use quaternions internally for rotations",
        "with_tbb": "Use Intel Threaded Building Blocks",
        "with_cholmod": "Enable the SuiteSparse CHOLMOD linear solver",
        "with_cuda": "Enable experimental CUDA acceleration",
        "with_cudss": "Enable the experimental cuDSS linear solver",
        "with_mkl": "Use Intel MKL through Eigen",
        "with_mosek": "Enable the MOSEK SDP solver",
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if Version(self.version) < "4.3":
            self.options.rm_safe("enable_boost_serialization")
            self.options.rm_safe("liegroup_preintegration")
            self.options.rm_safe("navstate_expmap")
            self.options.rm_safe("use_boost_features")
            self.options.rm_safe("with_cholmod")
            self.options.rm_safe("with_cuda")
            self.options.rm_safe("with_cudss")
            self.options.rm_safe("with_mosek")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_tbb:
            self.options["onetbb"].tbbmalloc = True
        if Version(self.version) >= "4.3" and self.options.default_allocator == "tcmalloc":
            self.options["gperftools"].build_cpu_profiler = True
        if not self.options.get_safe("with_cuda", False):
            del self.settings.cuda
        if (Version(self.version) < "4.3"
                or self.options.enable_boost_serialization
                or self.options.use_boost_features):
            for component in self._boost_build_components:
                setattr(self.options["boost"], f"with_{component}", True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.71.0]", transitive_headers=True)
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        if Version(self.version) >= "4.3":
            self.requires("spectra/[^1]")
        else:
            self.requires("spectra/[^1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_tbb:
            self.requires("onetbb/[>=2021]", transitive_headers=True, transitive_libs=True)
        if self.options.default_allocator == "tcmalloc":
            self.requires("gperftools/[^2.16]")
        if self.options.support_nested_dissection:
            self.requires("metis/[^5.1]", transitive_headers=True, transitive_libs=True)
        if Version(self.version) >= "4.3":
            self.requires("suitesparse-ccolamd/[^3.3]", transitive_headers=False, transitive_libs=not self.options.shared)
            if self.options.with_cholmod:
                self.requires("suitesparse-cholmod/[^5.3]", transitive_headers=False, transitive_libs=not self.options.shared)
            if self.options.with_mosek:
                self.requires("mosek/[>=10.2 <13]", transitive_headers=False, transitive_libs=not self.options.shared)
            if self.options.with_mkl:
                self.requires("onemkl/[*]", transitive_headers=True, transitive_libs=True)
            if self.options.with_cuda:
                self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)
                self.cuda.requires("cusolver", transitive_headers=False, transitive_libs=True)
                self.cuda.requires("cusparse", transitive_headers=True, transitive_libs=True)
            if self.options.with_cudss:
                self.requires("cudss/[>=0.8]", transitive_headers=False, transitive_libs=True)

    @property
    def _boost_build_components(self):
        if Version(self.version) >= "4.3":
            return ["chrono", "graph", "program_options", "random", "serialization", "timer"]
        return ["chrono", "date_time", "filesystem", "program_options", "regex", "serialization", "thread", "timer"]

    @property
    def _boost_public_components(self):
        if Version(self.version) < "4.3":
            return self._boost_build_components
        if not (self.options.enable_boost_serialization or self.options.use_boost_features):
            return []
        components = ["graph", "serialization"]
        if not self.options.disable_new_timers:
            components.append("chrono")
            components.append("timer")
        return components

    def validate(self):
        if Version(self.version) >= "4.3":
            check_min_cppstd(self, 17)
        else:
            check_min_cppstd(self, 11)

        if self.options.with_tbb:
            if self.options.default_allocator in [None, "TBB"]:
                if not self.dependencies["onetbb"].options.tbbmalloc:
                    raise ConanInvalidConfiguration("GTSAM with TBB requires onetbb/*:tbbmalloc=True")
            elif self.options.default_allocator != "tcmalloc":
                raise ConanInvalidConfiguration(f"with_tbb cannot be used with default_allocator={self.options.default_allocator}")
        elif self.options.default_allocator == "TBB":
            raise ConanInvalidConfiguration("default_allocator=TBB requires with_tbb=True")

        if self.options.get_safe("with_cudss") and not self.options.with_cuda:
            raise ConanInvalidConfiguration("with_cudss=True requires with_cuda=True")
        if self.options.get_safe("with_cuda"):
            self.cuda.validate_settings()
            self.cuda.check_min_cuda_architecture(60)
        if self.options.get_safe("with_mosek") and not self.dependencies["mosek"].options.fusion_cxx:
            raise ConanInvalidConfiguration("with_mosek=True requires mosek/*:fusion_cxx=True")

        check_min_vs(self, "191")

        if "4.1" <= Version(self.version) < "4.2" and is_msvc(self) and self.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} does not support shared builds with MSVC")

        if self.options.support_nested_dissection and self.dependencies["metis"].options.with_64bit_types:
            raise ConanInvalidConfiguration("GTSAM does not support METIS with 64-bit types")

    def build_requirements(self):
        if self.options.get_safe("with_cuda"):
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        if Version(self.version) < "4.3":
            replace_in_file(self, "CMakeLists.txt",
                            "cmake_minimum_required(VERSION 3.0)",
                            "cmake_minimum_required(VERSION 3.5)")
        if self.version == "4.1.1":
            replace_in_file(self, "cmake/GtsamMakeConfigFile.cmake", "${${PACKAGE_NAME}_VERSION}", f'"{self.version}"')

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_PROJECT_GTSAM_INCLUDE"] = "conan_deps.cmake"

        tc.variables["GTSAM_BUILD_UNSTABLE"] = self.options.build_unstable
        tc.variables["GTSAM_UNSTABLE_BUILD_PYTHON"] = False
        tc.variables["GTSAM_UNSTABLE_INSTALL_MATLAB_TOOLBOX"] = self.options.install_matlab_toolbox
        tc.variables["GTSAM_USE_QUATERNIONS"] = self.options.use_quaternions
        tc.variables["GTSAM_POSE3_EXPMAP"] = self.options.pose3_expmap
        tc.variables["GTSAM_ROT3_EXPMAP"] = self.options.rot3_expmap
        tc.variables["GTSAM_ENABLE_CONSISTENCY_CHECKS"] = self.options.enable_consistency_checks
        tc.variables["GTSAM_WITH_TBB"] = self.options.with_tbb
        tc.variables["GTSAM_WITH_EIGEN_MKL"] = self.options.with_mkl
        tc.variables["GTSAM_THROW_CHEIRALITY_EXCEPTION"] = self.options.throw_cheirality_exception
        tc.variables["GTSAM_BUILD_PYTHON"] = False
        tc.variables["GTSAM_INSTALL_MATLAB_TOOLBOX"] = self.options.install_matlab_toolbox
        tc.variables["GTSAM_ALLOW_DEPRECATED_SINCE_V4"] = self.options.allow_deprecated
        tc.variables["GTSAM_ALLOW_DEPRECATED_SINCE_V41"] = self.options.allow_deprecated
        tc.variables["GTSAM_ALLOW_DEPRECATED_SINCE_V42"] = self.options.allow_deprecated
        tc.variables["GTSAM_SUPPORT_NESTED_DISSECTION"] = self.options.support_nested_dissection
        tc.variables["GTSAM_TANGENT_PREINTEGRATION"] = self.options.tangent_preintegration
        tc.variables["GTSAM_SLOW_BUT_CORRECT_BETWEENFACTOR"] = self.options.slow_but_correct_betweenfactor
        tc.variables["GTSAM_BUILD_WITH_CCACHE"] = False

        if self.options.default_allocator is not None:
            tc.variables["GTSAM_DEFAULT_ALLOCATOR"] = self.options.default_allocator

        tc.variables["GTSAM_BUILD_TYPE_POSTFIXES"] = self.options.build_type_postfixes
        tc.variables["GTSAM_BUILD_WITH_MARCH_NATIVE"] = self.options.build_with_march_native
        tc.variables["GTSAM_DISABLE_NEW_TIMERS"] = self.options.disable_new_timers
        tc.variables["GTSAM_INSTALL_CPPUNITLITE"] = self.options.install_cppunitlite
        tc.variables["GTSAM_USE_SYSTEM_EIGEN"] = True
        tc.variables["GTSAM_MEX_BUILD_STATIC_MODULE"] = False
        tc.variables["GTSAM_BUILD_TESTS"] = False
        tc.variables["GTSAM_BUILD_EXAMPLES_ALWAYS"] = False
        tc.variables["GTSAM_BUILD_TIMING_ALWAYS"] = False
        tc.variables["GTSAM_BUILD_DOCS"] = False
        tc.variables["GTSAM_BUILD_DOC_HTML"] = False
        tc.variables["GTSAM_BUILD_DOC_LATEX"] = False
        if Version(self.version) >= "4.3":
            tc.variables["GTSAM_ALLOW_DEPRECATED_SINCE_V43"] = self.options.allow_deprecated
            tc.variables["GTSAM_DT_MERGING"] = True
            tc.variables["GTSAM_ENABLE_BOOST_SERIALIZATION"] = self.options.enable_boost_serialization
            tc.variables["GTSAM_ENABLE_TIMING"] = False
            tc.variables["GTSAM_HYBRID_TIMING"] = False
            tc.variables["GTSAM_LIEGROUP_PREINTEGRATION"] = self.options.liegroup_preintegration
            tc.variables["GTSAM_NAVSTATE_EXPMAP"] = self.options.navstate_expmap
            tc.variables["GTSAM_SLOW_BUT_CORRECT_EXPMAP"] = True
            tc.variables["GTSAM_TBB_BOUNDED_MEMORY_GROWTH"] = False
            tc.variables["GTSAM_USE_BOOST_FEATURES"] = self.options.use_boost_features
            tc.variables["GTSAM_USE_SYSTEM_CCOLAMD"] = True
            tc.variables["GTSAM_USE_SYSTEM_METIS"] = True
            tc.variables["GTSAM_USE_SYSTEM_SPECTRA"] = True
            tc.variables["GTSAM_CONAN_WITH_CHOLMOD"] = self.options.with_cholmod
            tc.variables["GTSAM_WITH_MOSEK"] = self.options.with_mosek
            tc.variables["GTSAM_ENABLE_CUDA"] = self.options.with_cuda
            tc.variables["GTSAM_ENABLE_CUDSS"] = self.options.with_cudss
            tc.variables["GTSAM_ENABLE_ASAN"] = False
            tc.variables["GTSAM_ENABLE_GEOGRAPHICLIB"] = False
            tc.variables["GTSAM_ENABLE_GPERFTOOLS"] = self.options.default_allocator == "tcmalloc"
            tc.variables["GTSAM_ENABLE_MEMORY_SANITIZER"] = False
            tc.variables["GTSAM_BUILD_WITH_PRECOMPILED_HEADERS"] = False
            tc.variables["GTSAM_BUILD_WITH_WERROR"] = False
        else:
            tc.variables["GTSAM_USE_SYSTEM_METIS"] = False
            tc.variables["GTSAM_INSTALL_GEOGRAPHICLIB"] = False

        tc.variables["Boost_USE_STATIC_LIBS"] = not self.dependencies["boost"].options.shared
        tc.variables["Boost_NO_SYSTEM_PATHS"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("gperftools", "cmake_file_name", "GooglePerfTools")
        deps.set_property("gperftools::tcmalloc_minimal", "cmake_target_name", "tcmalloc")
        deps.set_property("gperftools", "cmake_additional_variables_prefixes", [
            "GOOGLE_PERFTOOLS",
            "GPERFTOOLS",
        ])
        deps.set_property("gperftools", "cmake_extra_variables", {
            "GOOGLE_PERFTOOLS_FOUND": True,
            "GPERFTOOLS_FOUND": True,
            "GPERFTOOLS_TCMALLOC": "tcmalloc",
            "GPERFTOOLS_PROFILER": "gperftools::profiler",
        })
        if Version(self.version) >= "4.3":
            deps.set_property("metis", "cmake_file_name", "metis")
            deps.set_property("metis", "cmake_target_name", "metis")
            deps.set_property("mosek", "cmake_file_name", "MOSEK")
            deps.set_property("cudss::cudss_", "cmake_target_name", "cudss::cudss")
        else:
            deps.set_property("metis", "cmake_target_name", "metis-gtsam-if")
        deps.generate()

        if self.options.get_safe("with_cuda"):
            self.cuda.CudaToolchain().generate()

    def _patch_sources(self):
        if is_msvc(self):
            path = os.path.join(self.source_folder, "cmake", "GtsamBuildTypes.cmake")
            replace_in_file(self, path, "/MDd", "/MD")
            replace_in_file(self, path, "/MD", f"/{msvc_runtime_flag(self)}")
        if Version(self.version) < "4.3":
            save(self, os.path.join(self.source_folder, "cmake", "HandleMetis.cmake"),
                 "find_package(metis REQUIRED CONFIG)\n")
        tbb = os.path.join(self.source_folder, "cmake", "HandleTBB.cmake")
        replace_in_file(self, tbb, "find_package(TBB 4.4 ", "find_package(TBB ")
        if Version(self.version) < "4.2.1":
            replace_in_file(self, tbb,
                            "list(APPEND GTSAM_ADDITIONAL_LIBRARIES tbb tbbmalloc)",
                            "list(APPEND GTSAM_ADDITIONAL_LIBRARIES TBB::tbb TBB::tbbmalloc)")
        if Version(self.version) < "4.3":
            # Unvendor Spectra
            rmdir(self, os.path.join(self.source_folder, "gtsam", "3rdparty", "Spectra"))
            replace_in_file(self, os.path.join(self.source_folder, "gtsam", "sfm", "ShonanAveraging.cpp"),
                            "#include <SymEigsSolver.h>",
                            "#include <Spectra/SymEigsSolver.h>")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.BSD", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Keep lib/cmake/GTSAMCMakeTools
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake", "GTSAM"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake", "GTSAM_UNSTABLE"))

    def package_info(self):
        # GTSAM uses targets without a namespace prefix:
        # https://github.com/borglab/gtsam/blob/4.2.0/cmake/example_cmake_find_gtsam/CMakeLists.txt
        self.cpp_info.set_property("cmake_file_name", "GTSAM")
        gtsam = self.cpp_info.components["libgtsam"]
        gtsam.set_property("cmake_target_name", "gtsam")
        gtsam.libs = ["gtsam"]
        gtsam.builddirs = [os.path.join("lib", "cmake", "GTSAMCMakeTools")]
        gtsam.requires = [f"boost::{component}" for component in self._boost_public_components]
        gtsam.requires.append("boost::headers")
        gtsam.requires.append("eigen::eigen")
        gtsam.requires.append("spectra::spectra")
        if self.options.with_tbb:
            gtsam.requires.append("onetbb::libtbb")
            gtsam.requires.append("onetbb::tbbmalloc")
        if (Version(self.version) >= "4.3"
                and self.options.disable_new_timers
                and (self.options.enable_boost_serialization or self.options.use_boost_features)):
            gtsam.defines.append("GTSAM_DISABLE_NEW_TIMERS")
            gtsam.defines.append("BOOST_TIMER_ENABLE_DEPRECATED")
        if Version(self.version) >= "4.3" and self.options.with_mkl:
            gtsam.requires.append("onemkl::mkl")
        if self.options.default_allocator == "tcmalloc":
            gtsam.requires.append("gperftools::gperftools")
        if self.options.support_nested_dissection:
            if Version(self.version) >= "4.3":
                gtsam.requires.append("metis-gtsam-if")
            else:
                gtsam.requires.append("metis::metis")
        if Version(self.version) >= "4.3":
            gtsam.requires.append("suitesparse-ccolamd::suitesparse-ccolamd")
            if self.options.with_cholmod:
                gtsam.requires.append("suitesparse-cholmod::suitesparse-cholmod")
            if self.options.with_mosek:
                if self.options.shared:
                    gtsam.requires.append("mosek::fusion64")
                else:
                    gtsam.requires.append("gtsam_mosek_backend")
            if self.options.with_cuda:
                gtsam.defines.append("GTSAM_ENABLE_CUDA=1")
                gtsam.requires.append("cudart::cudart_")
                gtsam.requires.append("cusolver::cusolver_")
                gtsam.requires.append("cusparse::cusparse")
            if self.options.with_cudss:
                gtsam.defines.append("GTSAM_ENABLE_CUDSS=1")
                gtsam.requires.append("cudss::cudss_")
        if self.settings.os == "Windows":
            gtsam.system_libs = ["dbghelp"]
        if Version(self.version) >= "4.3" and is_msvc(self):
            gtsam.defines.append("_ENABLE_EXTENDED_ALIGNED_STORAGE")
            gtsam.defines.append("_USE_MATH_DEFINES")
            gtsam.cxxflags.append("/wd4267")
            gtsam.cxxflags.append("/permissive-")
        if Version(self.version) >= "4.3" and self.settings.compiler in ["clang", "apple-clang"]:
            if self.settings.compiler != "apple-clang" or Version(self.settings.compiler.version) >= "5":
                gtsam.cxxflags.append("-ftemplate-depth=1024")
        if self.options.build_with_march_native and not is_msvc(self) and self.settings.os != "QNX":
            if not (is_apple_os(self)
                    and self.settings.compiler == "apple-clang"
                    and Version(self.settings.compiler.version) < "15"
                    and self.settings.arch == "armv8"):
                gtsam.cxxflags.append("-march=native")

        if self.options.build_unstable:
            gtsam_unstable = self.cpp_info.components["libgtsam_unstable"]
            gtsam_unstable.set_property("cmake_target_name", "gtsam_unstable")
            gtsam_unstable.libs = ["gtsam_unstable"]
            gtsam_unstable.requires = ["libgtsam"]

        if self.options.install_cppunitlite:
            cppunitlite = self.cpp_info.components["gtsam_CppUnitLite"]
            cppunitlite.set_property("cmake_target_name", "CppUnitLite")
            cppunitlite.libs = ["CppUnitLite"]

        if Version(self.version) >= "4.3":
            cephes = self.cpp_info.components["cephes-gtsam"]
            cephes.set_property("cmake_target_name", "cephes-gtsam")
            cephes.set_property("cmake_target_aliases", ["cephes-gtsam-if"])
            cephes.libs = ["cephes-gtsam"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                cephes.system_libs = ["m"]
            gtsam.requires.append("cephes-gtsam")

            if self.options.support_nested_dissection:
                metis = self.cpp_info.components["metis-gtsam-if"]
                metis.set_property("cmake_target_name", "metis-gtsam-if")
                metis.requires = ["metis::metis"]

            if self.options.with_mosek and not self.options.shared:
                mosek = self.cpp_info.components["gtsam_mosek_backend"]
                mosek.set_property("cmake_target_name", "gtsam_mosek_backend")
                mosek.set_property("cmake_target_aliases", ["GTSAM::mosek_backend"])
                mosek.requires = ["mosek::fusion64"]

        if is_msvc(self) and not self.options.shared:
            for component in self.cpp_info.components.values():
                component.libs = [f"lib{lib}" for lib in component.libs if lib.startswith("gtsam")]
        if self.options.build_type_postfixes and self.settings.build_type != "Release":
            for component in self.cpp_info.components.values():
                component.libs = [f"{lib}{self.settings.build_type}" for lib in component.libs]
