import importlib
import io
import os
import sys
from pathlib import PurePath

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import load, mkdir
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    @property
    def _can_build(self):
        # FIXME: Python does not distribute debug libraries (use cci CPython recipe)
        if is_msvc(self) and self.settings.build_type == "Debug":
            return False
        # FIXME: apple-clang fails with 'ld: library not found for -lintl' in CI, despite working ok locally
        if self.settings.compiler == "apple-clang":
            return False
        return True

    @property
    def _python_interpreter(self):
        if getattr(sys, "frozen", False):
            return "python"
        return sys.executable

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["Python_EXECUTABLE"] = PurePath(self._python_interpreter).as_posix()
        tc.generate()
        deps = CMakeDeps(self)
        deps.build_context_activated.append("swig-matlab")
        deps.build_context_build_modules.append("swig-matlab")
        deps.generate()

    def build(self):
        self.run("swig -swiglib")
        if Version(self.dependencies.build["swig-matlab"].ref.version).major >= "4":
            self._test_new_backends()
        if self._can_build:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _test_new_backends(self):
        python_dir = os.path.join(self.build_folder, "python-stubs")
        matlab_dir = os.path.join(self.build_folder, "matlab")
        wasm_dir = os.path.join(self.build_folder, "wasm-js")
        for directory in (python_dir, matlab_dir, wasm_dir):
            mkdir(self, directory)

        python_interface = os.path.join(self.source_folder, "python_stubs.i")
        test_interface = os.path.join(self.source_folder, "test.i")
        self.run(f'swig -c++ -python -stubs -outdir "{python_dir}" '
                 f'-o "{os.path.join(python_dir, "test_wrap.cxx")}" "{python_interface}"')
        self.run(f'swig -c++ -matlab -outdir "{matlab_dir}" '
                 f'-o "{os.path.join(matlab_dir, "test_wrap.cxx")}" "{test_interface}"')
        self.run(f'swig -c++ -wasm-js -outdir "{wasm_dir}" '
                 f'-o "{os.path.join(wasm_dir, "test_wrap.cxx")}" "{test_interface}"')

        python_wrapper = load(self, os.path.join(python_dir, "test_wrap.cxx"))
        if "$isvoid" in python_wrapper:
            raise RuntimeError("SWIG did not expand $isvoid in the Python wrapper")
        stubs = load(self, os.path.join(python_dir, "python_stubs.pyi"))
        if "package_smoke" not in stubs:
            raise RuntimeError("SWIG did not emit %stubcode into the Python stub file")

    def _test_swig_module(self):
        sys.path.append(self.build_folder)
        sys.path.append(os.path.join(self.build_folder, str(self.settings.build_type)))
        # Could also simply use 'import PackageTest' but this makes pylint angry
        PackageTest = importlib.import_module("PackageTest")
        assert PackageTest.gcd(12, 16) == 4
        self.output.info("PackageTest.gcd(12, 16) ran successfully")
        assert PackageTest.cvar.foo == 3.14159265359
        self.output.info("PackageTest.cvar.foo == 3.14159265359 ran successfully")
        sys.path.pop()

    def test(self):
        if can_run(self):
            if self._can_build:
                self._test_swig_module()
        self.run("swig -swiglib")
        self.run("swig -version")
        self.run("swig -pcreversion")
        stdout = io.StringIO()
        self.run("swig --help", stdout=stdout)
        self.output.info("\n\n" + stdout.getvalue().split("General Options")[0].strip())
