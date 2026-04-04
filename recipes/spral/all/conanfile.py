import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, check_min_cstd, can_run, stdcpp_library, cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class SpralConan(ConanFile):
    name = "spral"
    description = "SPRAL: Sparse Parallel Robust Algorithms Library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ralna/spral"
    topics = ("sparse-linear-algebra", "direct-solver", "eigenvalue-solver")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
        "with_hwloc": [True, False],
        "with_cuda": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": True,
        "with_hwloc": True,
        "with_cuda": False,
    }
    implements = ["auto_shared_fpic"]
    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _fortran_compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return executables.get("fortran")

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.with_cuda:
            self.options.with_openmp.value = True
        else:
            del self.settings.cuda

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        self.requires("metis/[^5.1]")
        if self.options.with_hwloc:
            self.requires("hwloc/[^2.0]")
        if self.options.with_cuda:
            self.cuda.requires("cublas")
        if self.options.with_openmp:
            self.requires("openmp/system")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[^2.2]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def validate_build(self):
        if not self._fortran_compiler:
            raise ConanInvalidConfiguration(
                "A Fortran compiler is required. "
                "Please provide one by setting tools.build:compiler_executables={'fortran': '...'}."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["tests"] = False
        tc.project_options["examples"] = False
        tc.project_options["modules"] = False  # Don't install Fortran modules
        tc.project_options["openmp"] = self.options.with_openmp
        tc.project_options["gpu"] = self.options.with_cuda
        tc.project_options["libmetis_version"] = str(self.dependencies["metis"].ref.version.major)
        tc.generate()
        meson_ini = "conan_meson_cross.ini" if cross_building(self) else "conan_meson_native.ini"
        replace_in_file(self, meson_ini, "[binaries]", f"[binaries]\nfortran = '{self._fortran_compiler}'")

        deps = PkgConfigDeps(self)
        deps.set_property("cublas::cublas_", "pkg_config_name", "cublas")
        deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()
            # Meson runs a test executable that requires libcudart.so
            if can_run(self):
                VirtualRunEnv(self).generate(scope="build")

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENCE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["spral"]
        self.cpp_info.requires = ["lapack::lapack", "metis::metis"]
        if self.options.with_hwloc:
            self.cpp_info.requires.append("hwloc::hwloc")
        if self.options.with_cuda:
            self.cpp_info.requires.append("cublas::cublas_")
        if self.options.with_openmp:
            self.cpp_info.requires.append("openmp::openmp")
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs = ["m", "mvec"]
            if stdcpp_library(self):
                self.cpp_info.system_libs.append(stdcpp_library(self))
            if "gfortran" in self._fortran_compiler:
                self.cpp_info.system_libs.append("gfortran")
