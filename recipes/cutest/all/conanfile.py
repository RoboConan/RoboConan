import os

from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class CutestConan(ConanFile):
    name = "cutest"
    description = "Constrained and Unconstrained Testing Environment with safe threads for optimization software"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ralna/CUTEst"
    topics = ("optimization", "testing", "constrained-optimization", "unconstrained-optimization")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    options = {
        "quadruple": [True, False],
        "int64": [True, False],
    }
    default_options = {
        "quadruple": True,
        "int64": False,
    }
    languages = ["C"]

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def configure(self):
        if "arm" in str(self.settings.arch):
            self.options.quadruple.value = False

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        self.fortran.validate_settings()

    def validate_build(self):
        self.fortran.validate_build()

    def requirements(self):
        self.fortran.requires_runtime()

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["tests"] = False
        tc.project_options["quadruple"] = bool(self.options.quadruple)
        tc.project_options["int64"] = bool(self.options.int64)
        tc.project_options["modules"] = False
        tc.project_options["default_library"] = "shared"
        self.fortran.configure_meson_toolchain(tc)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()

    def package_info(self):
        suffix = "_64" if self.options.int64 else ""
        self.cpp_info.components["single"].libs = ["cutest_single" + suffix]
        self.cpp_info.components["double"].libs = ["cutest_double" + suffix]
        if self.options.quadruple:
            self.cpp_info.components["quadruple"].libs = ["cutest_quadruple" + suffix]
        for component in self.cpp_info.components.values():
            self.fortran.add_runtime_to_cpp_info(component)
