import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, check_min_cstd, can_run, stdcpp_library
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.13"


class SpralConan(ConanFile):
    name = "spral"
    description = "SPRAL: Sparse Parallel Robust Algorithms Library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ralna/spral"
    topics = ("sparse-linear-algebra", "direct-solver", "eigenvalue-solver")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda", "fortran"
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

    python_requires = ["conan-cuda/latest", "conan-fortran/latest", "conan-utils/latest"]
    python_requires_extend = "conan-cuda.Cuda", "conan-fortran.Fortran"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if is_msvc(self):
            # MSVC does not support the OpenMP task dependencies, task groups and
            # cancellation directives used by SPRAL, even with /openmp:experimental.
            self.options.with_openmp = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_cuda:
            self.options.with_openmp.value = True
        else:
            del self.settings.cuda
        if not self.options.with_openmp:
            self.options["metis"].with_openmp = False
            self.options["openblas"].threading = "serial"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        self.requires("metis/[^5.1]")
        self.fortran.requires_runtime()
        if self.options.with_hwloc:
            self.requires("hwloc/[^2.0]")
        if self.options.with_cuda:
            self.cuda.requires("cublas")
        if self.options.with_openmp:
            self.requires("openmp/system")

    def validate(self):
        self.fortran.validate_settings()
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        if mangling != self.fortran.mangling.value:
            raise ConanInvalidConfiguration(
                f"LAPACK uses {mangling}, but the configured Fortran toolchain uses {self.fortran.mangling.value}"
            )
        check_min_cppstd(self, 11)
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 99)

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def validate_build(self):
        self.fortran.validate_build()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["tests"] = False
        tc.project_options["examples"] = False
        tc.project_options["modules"] = False  # Don't install Fortran modules
        tc.project_options["openmp"] = bool(self.options.with_openmp)
        tc.project_options["gpu"] = bool(self.options.with_cuda)
        tc.project_options["libmetis_version"] = str(self.dependencies["metis"].ref.version.major)
        compiler_args = None
        if self.settings.os == "Windows" and self.fortran.compiler == "ifx":
            # SPRAL's Fortran sources use preprocessor conditionals on Windows.
            compiler_args = ["/fpp"]
        self.fortran.configure_meson_toolchain(tc, compiler_args=compiler_args)
        tc.generate()

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
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

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
        self.fortran.add_runtime_to_cpp_info(self.cpp_info)
