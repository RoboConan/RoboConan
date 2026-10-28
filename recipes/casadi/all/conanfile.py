import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.13"


class PackageConan(ConanFile):
    name = "casadi"
    description = "CasADi is a symbolic framework for automatic differentation and numeric optimization"
    license = "LGPL-3.0-or-only"
    homepage = "https://casadi.org"
    topics = ("optimization", "nonlinear", "numerical-calculations", "scientific-computing", "derivatives",
              "code-generation", "parameter-estimation", "optimal-control", "symbolic-manipulation",
              "algorithmic-differentation", "nonlinear-programming")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "enable_deprecated": [True, False],
        "threadsafe_symbolics": [True, False],
        "install_internal_headers": [True, False],
        "python_interface": [True, False],
        "octave_interface": [True, False],
        "matlab_interface": [True, False],
        "json_interface": [True, False],
        "with_blasfeo": [True, False],
        "with_l1_blas": [True, False],
        "with_alpaqa": [True, False],
        "with_ampl": [True, False],
        "with_blocksqp": [True, False],
        "with_bonmin": [True, False],
        "with_cbc": [True, False],
        "with_ccopt": [True, False],
        "with_clang": [True, False],
        "with_clarabel": [True, False],
        "with_clp": [True, False],
        "with_conopt": [True, False],
        "with_cplex": [True, False],
        "with_csparse": [True, False],
        "with_daqp": [True, False],
        "with_fatrop": [True, False],
        "with_fmi2": [True, False],
        "with_fmi3": [True, False],
        "with_ghc_filesystem": [True, False],
        "with_gurobi": [True, False],
        "with_highs": [True, False],
        "with_hpipm": [True, False],
        "with_hpmpc": [True, False],
        "with_hsl": [True, False],
        "with_ipopt": [True, False],
        "with_knitro": [True, False],
        "with_lapack": [True, False],
        "with_lacemodelica": [True, False],
        "with_libzip": [True, False],
        "with_madnlp": [True, False],
        "with_matlab_ipc": [True, False],
        "with_mumps": [True, False],
        "with_mosek": [True, False],
        "with_onnx": [True, False],
        "with_onnxruntime": [True, False],
        "with_ooqp": [True, False],
        "with_openmp": [True, False],
        "with_osqp": [True, False],
        "with_piqp": [True, False],
        "with_proxqp": [True, False],
        "with_pthread": [True, False],
        "with_qpoases": [True, False],
        "with_rumoca": [True, False],
        "with_sleqp": [True, False],
        "with_slicot": [True, False],
        "with_snopt": [True, False],
        "with_sundials": [True, False],
        "with_superscs": [True, False],
        "with_tinyxml": [True, False],
        "with_uno": [True, False],
        "with_worhp": [True, False],
        "with_zlib": [True, False],
        "with_xpress": [True, False],
    }
    default_options = {
        "enable_deprecated": True,
        "threadsafe_symbolics": False,
        "install_internal_headers": False,

        # Bindings
        "python_interface": False,
        "octave_interface": False,
        "matlab_interface": False,
        "json_interface": False,

        # BLAS implementations
        "with_blasfeo": False,
        "with_l1_blas": False,

        # Linear solvers
        "with_csparse": True,
        "with_lapack": True,
        "with_hsl": False,  # commercial
        "with_mumps": True,

        # Conic solvers
        "with_cbc": False,
        "with_clarabel": False,
        "with_clp": False,
        "with_cplex": False,  # commercial
        "with_daqp": False,
        "with_fatrop": True,  # also NLP
        "with_gurobi": False,  # commercial
        "with_highs": True,
        "with_hpipm": False,
        "with_hpmpc": False,
        "with_mosek": False,  # commercial
        "with_ooqp": False,
        "with_osqp": True,
        "with_piqp": False,
        "with_proxqp": True,
        "with_qpoases": True,
        "with_superscs": False,
        "with_xpress": False,  # commercial

        # NLP solvers
        "with_alpaqa": False,
        "with_ampl": False,  # commercial
        "with_blocksqp": True,
        "with_bonmin": False,
        "with_ccopt": False,
        "with_conopt": False,  # commercial
        "with_ipopt": True,
        "with_knitro": False,  # commercial
        "with_madnlp": False,
        "with_sleqp": False,
        "with_snopt": False,  # commercial
        "with_worhp": False,  # commercial

        # Discrete periodic Lyapunov Equation solver, matrix exponential
        "with_slicot": True,
        # integrator_cvodes, integrator_idas, rootfinder_kinsol
        "with_sundials": True,

        # Misc
        "with_clang": False,
        "with_fmi2": True,
        "with_fmi3": True,
        "with_ghc_filesystem": True,
        "with_lacemodelica": False,
        "with_libzip": True,
        "with_onnx": False,
        "with_onnxruntime": False,
        "with_matlab_ipc": False,
        "with_rumoca": False,
        "with_openmp": True,
        "with_pthread": False,
        "with_tinyxml": True,
        "with_uno": False,
        "with_zlib": True,

        "osqp/*:int32": True,
        "qdldl/*:int32": True,
        "sundials/*:build_arkode": False,
        "sundials/*:build_cvode": False,
        "sundials/*:build_ida": False,
        "superscs/*:casadi_compatibility": True,
    }

    def config_options(self):
        if Version(self.version) < "3.8":
            self.options.rm_safe("with_blasfeo")
            self.options.rm_safe("with_ccopt")
            self.options.rm_safe("with_lacemodelica")
            self.options.rm_safe("with_l1_blas")
            self.options.rm_safe("with_mosek")
            self.options.rm_safe("with_onnx")
            self.options.rm_safe("with_onnxruntime")
            self.options.rm_safe("with_piqp")
            self.options.rm_safe("with_uno")
            self.options.rm_safe("with_xpress")
        if Version(self.version) < "3.8.1":
            self.options.rm_safe("with_conopt")

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self._with_wasm_js:
            self.package_type = "static-library"
        if self.options.with_pthread:
            self.options.threadsafe_symbolics.value = True
        if self.options.with_blocksqp:
            self.options.with_qpoases.value = True
        if self.options.get_safe("with_lacemodelica"):
            self.options.with_ghc_filesystem.value = True
            self.options.with_onnx.value = True
            self.options.with_tinyxml.value = True
        if self.options.get_safe("with_onnxruntime"):
            self.options.with_onnx.value = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("with_blasfeo"):
            self.requires("blasfeo/[>=0.1 <1]")
        if self.options.get_safe("with_onnxruntime"):
            self.requires("onnxruntime/[^1.22]")
        if self.options.get_safe("with_onnx"):
            self.requires("onnx/[^1.18]")
        if self.options.with_alpaqa:
            self.requires("alpaqa/1.0.0-casadi.20230731")
        if self.options.with_bonmin:
            self.requires("coin-bonmin/[*]")
        if self.options.with_cbc:
            self.requires("coin-cbc/[^2.10.11]")
        if self.options.with_clang:
            # clang::CompilerInstance::createDiagnostics() is not compatible in v20
            self.requires("clang/[<20]")
        if self.options.with_clarabel:
            self.requires("clarabel/[*]")
        if self.options.with_clp:
            self.requires("coin-clp/[^1.17.9]")
        if self.options.get_safe("with_ccopt") or (
            Version(self.version) >= "3.8" and self.options.get_safe("with_madnlp")
        ):
            self.requires("madnlp-libmad/[^0.0.12]")
        if self.options.get_safe("with_conopt"):
            self.requires("conopt/[^4]")
        if self.options.with_cplex:
            self.requires("cplex/[*]")
        if self.options.with_csparse:
            self.requires("suitesparse-cxsparse/[^4.4.1]")
        if self.options.with_daqp:
            self.requires("daqp/[*]")
        if self.options.with_fatrop:
            self.requires("fatrop/[*]")
        if self.options.with_fmi2:
            self.requires("fmi2/[*]")
        if self.options.with_fmi3:
            self.requires("fmi3/[*]")
        if self.options.with_ghc_filesystem:
            self.requires("ghc-filesystem/[*]")
        if self.options.with_gurobi:
            self.requires("gurobi/[*]")
        if self.options.with_highs:
            self.requires("highs/[*]")
        if self.options.with_hpipm:
            self.requires("hpipm/[^0.1.3]")
        if self.options.with_hpmpc:
            self.requires("hpmpc/[*]")
        if self.options.with_hsl:
            self.requires("coin-hsl/[*]")
        if self.options.with_ipopt:
            self.requires("coin-ipopt/[^3.14.13]")
        if self.options.with_knitro:
            self.requires("knitro/[*]")
        if self.options.with_lapack:
            self.requires("lapack/latest")
        if self.options.get_safe("with_lacemodelica"):
            self.requires("lacemodelica/[^0.1.0]")
        if self.options.with_libzip:
            self.requires("libzip/[*]")
        if Version(self.version) < "3.8" and self.options.get_safe("with_madnlp"):
            self.requires("madnlp-mockup/89")
        if self.options.matlab_interface or self.options.with_matlab_ipc:
            self.requires("matlab-mockup/[*]")
        if self.options.with_mumps:
            self.requires("coin-mumps/[^3.0.5]")
        if self.options.get_safe("with_mosek"):
            self.requires("mosek/[^11]")
        if self.options.octave_interface:
            self.requires("octave-mockup/[*]")
        if self.options.with_ooqp:
            self.requires("ooqp/[*]")
        if self.options.with_openmp:
            self.requires("openmp/system")
        if self.options.with_osqp:
            self.requires("osqp/[>=0.5.0 <1]")
        if self.options.get_safe("with_piqp"):
            self.requires("piqp/[^0.6.2]")
        if self.options.with_proxqp:
            self.requires("proxsuite/[*]")
        if self.options.with_pthread and self.settings.os == "Windows":
            self.requires("pthreads4w/[^3.0.0]")
        if self.options.with_qpoases:
            self.requires("qpoases/3.2.2-casadi")
        if self.options.with_rumoca:
            self.requires("rumoca/[*]")
        if self.options.with_sleqp:
            self.requires("sleqp/[*]")
        if self.options.with_slicot:
            self.requires("slicot/[*]")
        if self.options.with_snopt:
            self.requires("snopt-mockup/[*]")
        if self.options.with_sundials:
            self.requires("sundials/[^2.5]")
        if self.options.with_superscs:
            self.requires("superscs/[*]")
        if self.options.with_tinyxml:
            self.requires("tinyxml2/[*]")
        if self.options.get_safe("with_uno"):
            self.requires("uno/[>=2.7.2 <3]")
        if self.options.with_worhp:
            self.requires("worhp/[*]")
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.get_safe("with_xpress"):
            self.requires("xpress/[^9]")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.options.with_alpaqa:
            check_min_cppstd(self, 20)
        if self.options.get_safe("with_uno"):
            check_min_cppstd(self, 17)
        compiler = self.settings.compiler
        if self._with_wasm_js and (compiler != "emcc" or Version(compiler.version) < "6"):
            raise ConanInvalidConfiguration("The WASM interface requires Emscripten 6 or newer")
        if self.options.with_osqp and not self.dependencies["osqp"].options.int32:
            raise ConanInvalidConfiguration("The OSQP interface requires osqp:int32=True")
        if self.options.with_superscs and not self.dependencies["superscs"].options.casadi_compatibility:
            raise ConanInvalidConfiguration("The SuperSCS interface requires superscs:casadi_compatibility=True")
        if self.options.with_pthread and self.settings.compiler == "msvc":
            raise ConanInvalidConfiguration("with_pthread=True is not supported for MSVC")
        if self.options.matlab_interface and self.options.octave_interface:
            raise ConanInvalidConfiguration("matlab_interface and octave_interface cannot be enabled at the same time")
        if self.options.with_lapack:
            if self.dependencies["lapack"].extension_properties["fortran_name_mangling"] != "lower_underscore":
                raise ConanInvalidConfiguration("CasADi requires LAPACK with lower_underscore names")

    @property
    def _with_wasm_js(self):
        return Version(self.version) >= "3.8" and self.settings.os == "Emscripten"

    @property
    def _swig_required(self):
        return any([
            self.options.python_interface,
            self.options.octave_interface,
            self.options.matlab_interface,
            self.options.json_interface,
            self._with_wasm_js,
        ])

    def build_requirements(self):
        if self._with_wasm_js:
            self.tool_requires("cmake/[>=3.16.3 <5]")
            self.tool_requires("emsdk/[^6]")
        if self._swig_required:
            if Version(self.version) >= "3.8":
                self.tool_requires("swig-matlab/[~4.4.0]")
            else:
                self.tool_requires("swig-matlab/[~3.0.11]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Everything is unvendored
        rmdir(self, "external_packages")
        save(self, "external_packages/CMakeLists.txt", "")
        rm(self, "Find*.cmake", "cmake")
        # Use the regular CMake installation layout on all platforms
        replace_in_file(self, "CMakeLists.txt", "WITH_SELFCONTAINED OR (WIN32 AND NOT CYGWIN)", "FALSE")
        replace_in_file(self, "CMakeLists.txt", "file(RELATIVE_PATH REL_LIB_PREFIX", "set(REL_LIB_PREFIX lib) #")
        replace_in_file(self, "CMakeLists.txt", "file(RELATIVE_PATH REL_CMAKE_PREFIX", "set(REL_CMAKE_PREFIX lib/cmake/casadi) #")
        replace_in_file(self, "casadi/CMakeLists.txt", "file(RELATIVE_PATH TREL_LIB_PREFIX", "set(TREL_LIB_PREFIX lib) #")
        replace_in_file(self, "casadi/CMakeLists.txt", "file(RELATIVE_PATH TREL_BIN_PREFIX", "set(TREL_BIN_PREFIX bin) #")
        replace_in_file(self, "casadi/core/CMakeLists.txt", "file(RELATIVE_PATH TREL_BIN_PREFIX", "set(TREL_BIN_PREFIX bin) #")
        replace_in_file(self, "casadi/core/CMakeLists.txt", "file(RELATIVE_PATH TREL_INCLUDE_PREFIX", "set(TREL_INCLUDE_PREFIX include) #")
        # The custom SWIG crashes with SIGILL inside Source/Modules/lang.cxx:format_paramlist() when the customdoc feature is enabled
        replace_in_file(self, "swig/casadi.i", '%feature("customdoc", "1");', '%feature("customdoc", "0");')
        # No need to copy the mock octave_adapter in Conan
        replace_in_file(self, "swig/matlab/CMakeLists.txt", "install(FILES ${OCTINTERP_LOCATION} DESTINATION ${LIB_PREFIX})", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        tc.cache_variables["WITH_EXAMPLES"] = False
        tc.cache_variables["USE_CXX11"] = True
        tc.cache_variables["WITH_PYTHON"] = self.options.python_interface
        tc.cache_variables["WITH_MATLAB"] = self.options.matlab_interface
        tc.cache_variables["WITH_OCTAVE"] = self.options.octave_interface
        tc.cache_variables["WITH_JSON"] = self.options.json_interface
        tc.cache_variables["WITH_JULIA"] = False
        tc.cache_variables["INSTALL_INTERNAL_HEADERS"] = self.options.install_internal_headers
        tc.cache_variables["ENABLE_STATIC"] = not self.options.get_safe("shared", True) or self._with_wasm_js
        tc.cache_variables["ENABLE_SHARED"] = self.options.get_safe("shared", True) and not self._with_wasm_js
        tc.cache_variables["WITH_WASM_JS"] = self._with_wasm_js
        tc.cache_variables["WITH_OPENMP"] = self.options.with_openmp
        tc.cache_variables["WITH_THREAD"] = self.options.with_pthread
        tc.cache_variables["WITH_THREAD_MINGW"] = False
        tc.cache_variables["WITH_THREADSAFE_SYMBOLICS"] = self.options.threadsafe_symbolics
        tc.cache_variables["WITH_DEPRECATED_FEATURES"] = self.options.enable_deprecated
        tc.cache_variables["WITH_BUILD_REQUIRED"] = False
        tc.cache_variables["WITH_BUILD_SUNDIALS"] = False
        tc.cache_variables["WITH_BUILD_CSPARSE"] = False
        tc.cache_variables["WITH_BUILD_TINYXML"] = False
        tc.cache_variables["CMAKE_Fortran_COMPILER"] = ""
        tc.cache_variables["Fortran_language_works"] = True
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0148"] = "OLD"
        tc.cache_variables["PYTHON_PREFIX"] = os.path.join(self.package_folder, "lib/python3/site-packages").replace("\\", "/")
        tc.cache_variables["MATLAB_PREFIX"] = os.path.join(self.package_folder, "lib/matlab").replace("\\", "/")
        tc.cache_variables["MATLAB_MEX_EXT"] = "mex"
        tc.cache_variables["OCTAVE_MEX_EXT"] = "oct"

        tc.cache_variables["WITH_MATLAB_IPC"] = self.options.with_matlab_ipc
        tc.cache_variables["WITH_CORE_BLAS_DEPENDENCY"] = self.options.with_lapack and not self.dependencies["blas"].options.shared
        tc.cache_variables["WITH_L1_BLAS"] = self.options.get_safe("with_l1_blas", False)
        tc.cache_variables["WITH_FMI2"] = self.options.with_fmi2
        tc.cache_variables["WITH_FMI3"] = self.options.with_fmi3
        tc.cache_variables["WITH_SUNDIALS"] = self.options.with_sundials
        tc.cache_variables["WITH_CSPARSE"] = self.options.with_csparse
        tc.cache_variables["WITH_HPIPM"] = self.options.with_hpipm
        tc.cache_variables["WITH_HPMPC"] = self.options.with_hpmpc
        tc.cache_variables["WITH_FATROP"] = self.options.with_fatrop
        tc.cache_variables["WITH_SUPERSCS"] = self.options.with_superscs
        tc.cache_variables["WITH_OSQP"] = self.options.with_osqp
        tc.cache_variables["WITH_CLARABEL"] = self.options.with_clarabel
        tc.cache_variables["WITH_RUMOCA"] = self.options.with_rumoca
        tc.cache_variables["WITH_PROXQP"] = self.options.with_proxqp
        tc.cache_variables["WITH_TINYXML"] = self.options.with_tinyxml
        tc.cache_variables["WITH_CLANG"] = self.options.with_clang
        tc.cache_variables["WITH_LAPACK"] = self.options.with_lapack
        tc.cache_variables["WITH_QPOASES"] = self.options.with_qpoases
        tc.cache_variables["WITH_PIQP"] = self.options.get_safe("with_piqp", False)
        tc.cache_variables["WITH_BLOCKSQP"] = self.options.with_blocksqp
        tc.cache_variables["WITH_SLEQP"] = self.options.with_sleqp
        tc.cache_variables["WITH_IPOPT"] = self.options.with_ipopt
        tc.cache_variables["WITH_MADNLP"] = self.options.get_safe("with_madnlp", False)
        if Version(self.version) >= "3.8":
            tc.cache_variables["WITH_CCOPT"] = self.options.with_ccopt
            tc.cache_variables["WITH_LACEMODELICA"] = self.options.with_lacemodelica
            tc.cache_variables["WITH_UNO"] = self.options.with_uno
        tc.cache_variables["WITH_MOSEK"] = self.options.get_safe("with_mosek", False)
        tc.cache_variables["WITH_ONNX"] = self.options.get_safe("with_onnx", False)
        tc.cache_variables["WITH_ONNX_RUNTIME"] = self.options.get_safe("with_onnxruntime", False)
        tc.cache_variables["WITH_KNITRO"] = self.options.with_knitro
        tc.cache_variables["WITH_SNOPT"] = self.options.with_snopt
        tc.cache_variables["WITH_WORHP"] = self.options.with_worhp
        tc.cache_variables["WITH_CPLEX"] = self.options.with_cplex
        tc.cache_variables["WITH_GUROBI"] = self.options.with_gurobi
        tc.cache_variables["WITH_BONMIN"] = self.options.with_bonmin
        tc.cache_variables["WITH_CBC"] = self.options.with_cbc
        tc.cache_variables["WITH_CLP"] = self.options.with_clp
        tc.cache_variables["WITH_CONOPT"] = self.options.get_safe("with_conopt", False)
        tc.cache_variables["WITH_MUMPS"] = self.options.with_mumps
        tc.cache_variables["WITH_HSL"] = self.options.with_hsl
        tc.cache_variables["WITH_HIGHS"] = self.options.with_highs
        tc.cache_variables["WITH_DAQP"] = self.options.with_daqp
        tc.cache_variables["WITH_ALPAQA"] = self.options.with_alpaqa
        tc.cache_variables["WITH_ZLIB"] = self.options.with_zlib
        tc.cache_variables["WITH_XPRESS"] = self.options.get_safe("with_xpress", False)
        tc.cache_variables["WITH_LIBZIP"] = self.options.with_libzip
        tc.cache_variables["WITH_GHC_FILESYSTEM"] = self.options.with_ghc_filesystem
        tc.cache_variables["WITH_OOQP"] = self.options.with_ooqp
        tc.cache_variables["WITH_SQIC"] = False
        tc.cache_variables["WITH_AMPL"] = self.options.with_ampl
        tc.cache_variables["WITH_SLICOT"] = self.options.with_slicot
        tc.cache_variables["WITH_BLASFEO"] = self.options.get_safe("with_blasfeo", False)
        tc.cache_variables["WITH_SPRAL"] = False  # only used to build Ipopt
        tc.cache_variables["WITH_DSDP"] = False  # not used anywhere
        tc.cache_variables["WITH_OPENCL"] = False  # not used anywhere
        tc.cache_variables["WITH_MOCKUP_REQUIRED"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("alpaqa", "cmake_target_name", "alpaqa")
        deps.set_property("blasfeo", "cmake_file_name", "BLASFEO")
        deps.set_property("blasfeo", "cmake_target_name", "blasfeo")
        deps.set_property("clang", "cmake_file_name", "CLANG")
        deps.set_property("coin-bonmin", "cmake_file_name", "BONMIN")
        deps.set_property("coin-bonmin", "cmake_target_name", "bonmin")
        deps.set_property("coin-cbc", "cmake_file_name", "CBC")
        deps.set_property("coin-cbc", "cmake_target_name", "cbc")
        deps.set_property("coin-clp", "cmake_file_name", "CLP")
        deps.set_property("coin-clp", "cmake_target_name", "clp")
        deps.set_property("coin-hsl", "cmake_file_name", "HSL")
        deps.set_property("coin-hsl", "cmake_target_name", "hsl::hsl")
        deps.set_property("coin-ipopt", "cmake_file_name", "IPOPT")
        deps.set_property("coin-ipopt", "cmake_target_name", "ipopt")
        deps.set_property("coin-mumps", "cmake_file_name", "MUMPS")
        deps.set_property("coin-mumps", "cmake_target_name", "mumps")
        deps.set_property("clarabel", "cmake_target_name", "clarabel")
        deps.set_property("conopt", "cmake_file_name", "CONOPT")
        deps.set_property("conopt::conopt_", "cmake_target_name", "conopt::conopt")
        deps.set_property("cplex", "cmake_file_name", "CPLEX")
        deps.set_property("daqp", "cmake_target_name", "daqp")
        deps.set_property("ecos", "cmake_file_name", "ECOS")
        deps.set_property("eigen", "cmake_file_name", "Eigen3")
        deps.set_property("fatrop", "cmake_file_name", "FATROP")
        deps.set_property("fmi2", "cmake_file_name", "FMI2")
        deps.set_property("fmi3", "cmake_file_name", "FMI3")
        deps.set_property("ghc-filesystem", "cmake_file_name", "ghcFilesystem")
        deps.set_property("gsl", "cmake_file_name", "GSL")
        deps.set_property("gurobi", "cmake_file_name", "GUROBI")
        deps.set_property("highs", "cmake_file_name", "HIGHS")
        deps.set_property("highs", "cmake_target_name", "highs")
        deps.set_property("hpmpc", "cmake_file_name", "HPMPC")
        deps.set_property("ipopt", "cmake_file_name", "IPOPT")
        deps.set_property("knitro", "cmake_file_name", "KNITRO")
        deps.set_property("lacemodelica", "cmake_file_name", "LACEMODELICA")
        deps.set_property("madnlp-mockup", "cmake_file_name", "MADNLP")
        deps.set_property("mosek", "cmake_file_name", "MOSEK")
        deps.set_property("mosek::mosek64", "cmake_target_name", "mosek::mosek")
        deps.set_property("matlab-mockup", "cmake_file_name", "MATLAB")
        deps.set_property("metis", "cmake_file_name", "METIS")
        deps.set_property("metis", "cmake_target_name", "metis::metis")
        deps.set_property("mumps", "cmake_file_name", "MUMPS")
        deps.set_property("octave-mockup", "cmake_file_name", "OCTAVE")
        deps.set_property("ooqp", "cmake_file_name", "OOQP")
        deps.set_property("ooqp", "cmake_target_name", "OOQP")
        deps.set_property("osqp", "cmake_file_name", "OSQP")
        deps.set_property("osqp", "cmake_target_name", "osqp::osqp")
        deps.set_property("onnx", "cmake_file_name", "ONNX")
        deps.set_property("onnx::libonnx", "cmake_target_name", "ONNX::onnx")
        deps.set_property("onnx::onnx_proto", "cmake_target_name", "ONNX::onnx_proto")
        deps.set_property("piqp", "cmake_file_name", "PIQP")
        deps.set_property("piqp::core", "cmake_target_name", "piqp")
        deps.set_property("proxsuite", "cmake_file_name", "PROXQP")
        deps.set_property("qpoases", "cmake_file_name", "QPOASES")
        deps.set_property("slicot", "cmake_file_name", "SLICOT")
        deps.set_property("snopt-mockup", "cmake_file_name", "SNOPT")
        deps.set_property("sqic", "cmake_file_name", "SQIC")
        deps.set_property("suitesparse-cxsparse", "cmake_file_name", "CSPARSE")
        deps.set_property("sundials", "cmake_file_name", "SUNDIALS")
        deps.set_property("superscs", "cmake_target_name", "superscs")
        deps.set_property("tinyxml2", "cmake_file_name", "TINYXML")
        deps.set_property("tinyxml2", "cmake_target_name", "tinyxml2::tinyxml2")
        deps.set_property("worhp", "cmake_file_name", "WORHP")
        deps.set_property("worhp", "cmake_target_name", "worhp::worhp")
        deps.set_property("xpress", "cmake_file_name", "XPRESS")
        deps.set_property("xpress::xprs", "cmake_target_name", "xpress::xpress")
        deps.set_property("lapack-reference::lapack", "cmake_target_name", "lapack-reference")
        if self._swig_required:
            deps.build_context_activated.append("swig-matlab")
            deps.build_context_build_modules.append("swig-matlab")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.json_interface:
            cmake.build(target="json")

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.json_interface:
            copy(self, "casadi.json", os.path.join(self.build_folder, "swig", "json"), os.path.join(self.package_folder, "share", "casadi"))
        if self._with_wasm_js:
            wasm_src = os.path.join(self.build_folder, "swig", "wasm-js")
            wasm_dst = os.path.join(self.package_folder, "share", "casadi", "wasm-js")
            for pattern in ("casadi.js", "casadi.d.ts", "casadi_wasm.js", "casadi_wasm.wasm",
                            "plugins.json", "libcasadi_*.so"):
                copy(self, pattern, wasm_src, wasm_dst)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "casadi")
        self.cpp_info.set_property("cmake_target_name", "casadi::casadi")
        self.cpp_info.set_property("pkg_config_name", "casadi")
        self.cpp_info.libs = ["casadi"]
        self.cpp_info.defines.append("CASADI_SNPRINTF=snprintf")
        optional_dependencies = {
            "with_alpaqa": "alpaqa::core",
            "with_blasfeo": "blasfeo::blasfeo",
            "with_bonmin": "coin-bonmin::libbonmin",
            "with_cbc": "coin-cbc::libcbc",
            "with_clarabel": "clarabel::clarabel",
            "with_clp": "coin-clp::libclp",
            "with_conopt": "conopt::conopt_",
            "with_cplex": "cplex::cplex_",
            "with_csparse": "suitesparse-cxsparse::suitesparse-cxsparse",
            "with_daqp": "daqp::core",
            "with_fatrop": "fatrop::fatrop",
            "with_fmi2": "fmi2::fmi2",
            "with_fmi3": "fmi3::fmi3",
            "with_ghc_filesystem": "ghc-filesystem::ghc-filesystem",
            "with_gurobi": "gurobi::gurobi_c",
            "with_highs": "highs::highs_",
            "with_hpipm": "hpipm::hpipm",
            "with_hpmpc": "hpmpc::hpmpc",
            "with_hsl": "coin-hsl::coin-hsl",
            "with_ipopt": "coin-ipopt::ipopt",
            "with_knitro": "knitro::core",
            "with_lapack": "lapack::lapack",
            "with_lacemodelica": "lacemodelica::lacemodelica",
            "with_libzip": "libzip::libzip",
            "with_mumps": "coin-mumps::coin-mumps",
            "with_mosek": "mosek::mosek64",
            "with_onnx": "onnx::libonnx",
            "with_onnxruntime": "onnxruntime::onnxruntime",
            "with_openmp": "openmp::openmp",
            "with_osqp": "osqp::osqp",
            "with_piqp": "piqp::core",
            "with_proxqp": "proxsuite::proxsuite",
            "with_qpoases": "qpoases::qpoases",
            "with_rumoca": "rumoca::rumoca",
            "with_sleqp": "sleqp::sleqp",
            "with_slicot": "slicot::slicot",
            "with_snopt": "snopt-mockup::snopt-mockup",
            "with_tinyxml": "tinyxml2::tinyxml2",
            "with_uno": "uno::uno",
            "with_worhp": "worhp::worhp",
            "with_xpress": "xpress::xprs",
            "with_zlib": "zlib-ng::zlib-ng",
        }
        for option, requirement in optional_dependencies.items():
            if self.options.get_safe(option, False):
                self.cpp_info.requires.append(requirement)

        if self.options.with_clang:
            self.cpp_info.requires.extend([
                "clang::clangFrontend",
                "clang::clangDriver",
                "clang::clangCodeGen",
                "clang::clangRewriteFrontend",
                "clang::clangSerialization",
                "clang::clangParse",
                "clang::clangSema",
                "clang::clangAnalysis",
                "clang::clangEdit",
                "clang::clangAST",
                "clang::clangLex",
                "clang::clangBasic",
            ])
        if self.options.get_safe("with_ccopt") or (
            Version(self.version) >= "3.8" and self.options.get_safe("with_madnlp")
        ):
            self.cpp_info.requires.append("madnlp-libmad::madnlp-libmad")
        if Version(self.version) < "3.8" and self.options.get_safe("with_madnlp"):
            self.cpp_info.requires.append("madnlp-mockup::madnlp_c")
        if self.options.matlab_interface or self.options.with_matlab_ipc:
            self.cpp_info.requires.append("matlab-mockup::matlab-mockup")
        if self.options.octave_interface:
            self.cpp_info.requires.append("octave-mockup::octave-mockup")
        if self.options.with_ooqp:
            self.cpp_info.requires.extend([
                "ooqp::ooqpgensparse",
                "ooqp::ooqpgondzio",
            ])
        if self.options.with_pthread and self.settings.os == "Windows":
            self.cpp_info.requires.append("pthreads4w::pthreads4w")
        if self.options.with_sundials:
            self.cpp_info.requires.extend([
                "sundials::sundials_cvodes",
                "sundials::sundials_idas",
                "sundials::sundials_kinsol",
                "sundials::sundials_nvecserial",
            ])
        if self.options.with_superscs:
            self.cpp_info.requires.append("superscs::scsindir")
        if self.options.threadsafe_symbolics:
            self.cpp_info.defines.append("CASADI_WITH_THREADSAFE_SYMBOLICS")
        if self.options.with_pthread:
            self.cpp_info.defines.append("CASADI_WITH_THREAD")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "dl"]
            if self.options.with_pthread:
                self.cpp_info.system_libs.append("pthread")

        if self.settings.os == "Windows":
            casadipath = os.path.join(self.package_folder, "bin")
        else:
            casadipath = os.path.join(self.package_folder, "lib")
        self.runenv_info.define_path("CASADIPATH", casadipath)
        if Version(self.version) >= "3.8":
            self.runenv_info.define_path("CASADI_PLUGIN_SEARCH_PATH", casadipath)

        if self.options.python_interface:
            self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "lib/python3/site-packages"))
        if self.options.octave_interface or self.options.matlab_interface:
            self.runenv_info.prepend_path("MATLABPATH", os.path.join(self.package_folder, "lib/matlab"))
        if self.options.json_interface:
            self.cpp_info.resdirs.append("share/casadi")
        if self._with_wasm_js:
            self.cpp_info.resdirs.append("share/casadi/wasm-js")
