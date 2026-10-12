import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.scm import Version


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        if self.settings.os == "Emscripten":
            self.tool_requires("emsdk/[^6]")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        opts = self.dependencies["casadi"].options
        plugin_options = {
            "with_blasfeo": "TEST_BLAS_BLASFEO",
            "with_ccopt": "TEST_NLPSOL_CCOPT",
            "with_conopt": "TEST_NLPSOL_CONOPT",
            "with_fatrop": "TEST_NLPSOL_FATROP",
            "with_highs": "TEST_CONIC_HIGHS",
            "with_hpipm": "TEST_CONIC_HPIPM",
            "with_ipopt": "TEST_NLPSOL_IPOPT",
            "with_lacemodelica": "TEST_MODELICAPARSER_LACEMODELICA",
            "with_lapack": "TEST_LINSOL_LAPACK",
            "with_madnlp": "TEST_NLPSOL_MADNLP",
            "with_mosek": "TEST_CONIC_MOSEK",
            "with_onnx": "TEST_GRAPHMODEL_ONNX",
            "with_onnxruntime": "TEST_ONNXBACKEND_ORT",
            "with_openmp": "TEST_OPENMP_MAP",
            "with_osqp": "TEST_CONIC_OSQP",
            "with_piqp": "TEST_CONIC_PIQP",
            "with_proxqp": "TEST_CONIC_PROXQP",
            "with_qpoases": "TEST_CONIC_QPOASES",
            "with_sundials": "TEST_INTEGRATOR_CVODES",
            "with_uno": "TEST_NLPSOL_UNO",
            "with_xpress": "TEST_CONIC_XPRESS",
        }
        for option, define in plugin_options.items():
            if opts.get_safe(option, False):
                tc.preprocessor_definitions[define] = None
        if (Version(self.dependencies["casadi"].ref.version) >= "3.8"
                and opts.get_safe("with_madnlp", False)):
            tc.preprocessor_definitions["TEST_NLPSOL_MADNLP_FUNCTIONAL"] = None
        if Version(self.dependencies["casadi"].ref.version) >= "3.8.1":
            tc.preprocessor_definitions["TEST_ROOTFINDER_BISECTION"] = None
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        dependency = self.dependencies["casadi"]
        if (Version(dependency.ref.version) >= "3.8"
                and self.settings.os == "Emscripten"):
            wasm_dir = os.path.join(dependency.package_folder, "share", "casadi", "wasm-js")
            self.run(f"node {os.path.join(self.source_folder, 'test_wasm.js')} {wasm_dir}")
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "test_package")
            self.run(bin_path, env="conanrun")
