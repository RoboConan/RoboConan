import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        opts = self.dependencies["boost"].options
        tc = CMakeToolchain(self)
        tc.cache_variables["Boost_USE_STATIC_LIBS"] = not opts.get_safe("shared")
        tc.cache_variables["WITH_CHRONO"] = opts.with_chrono
        tc.cache_variables["WITH_COROUTINE"] = opts.with_coroutine
        tc.cache_variables["WITH_FIBER"] = opts.with_fiber
        tc.cache_variables["WITH_JSON"] = opts.get_safe("with_json", False)
        tc.cache_variables["WITH_LOCALE"] = opts.with_locale
        tc.cache_variables["WITH_NOWIDE"] = opts.get_safe("with_nowide", False)
        tc.cache_variables["WITH_NUMPY"] = opts.get_safe("with_numpy", False)
        tc.cache_variables["WITH_PROCESS"] = opts.get_safe("with_process", False)
        tc.cache_variables["WITH_PYTHON"] = opts.with_python
        tc.cache_variables["WITH_RANDOM"] = opts.with_random
        tc.cache_variables["WITH_REGEX"] = opts.with_regex
        tc.cache_variables["WITH_STACKTRACE"] = opts.with_stacktrace
        tc.cache_variables["WITH_TEST"] = opts.with_test
        tc.cache_variables["WITH_URL"] = opts.get_safe("with_url", True)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        for file in os.listdir(self.cpp.build.bindirs[0]):
            if file.startswith("test_boost_"):
                if self.settings.os == "Windows" and not file.endswith(".exe"):
                    continue
                bin_path = os.path.join(self.cpp.build.bindirs[0], file)
                self.run(bin_path, env="conanrun")
