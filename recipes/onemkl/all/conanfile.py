import os
from functools import cached_property
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OneMKLConan(ConanFile):
    name = "onemkl"
    description = "Intel oneAPI Math Kernel Library (oneMKL)"
    # https://intel.ly/393CijO
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html"
    topics = ("intel", "oneapi", "math", "blas", "lapack", "linear-algebra", "pre-built")
    package_type = "library"  # shared-library on Linux
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "interface": ["lp64", "ilp64"],
        "sdl": [True, False],
        "interface_type": ["intel", "gf"],
        "threading": ["sequential", "tbb", "intel", "gnu"],
        "blas95": [True, False],
        "lapack95": [True, False],
        "sycl": [True, False],
        "omp_offload": [True, False],
        "blacs": [True, False],
        "mpi": ["intelmpi", "openmpi"],
        "compatibility_headers": [True, False],
        # SYCL submodules
        "sycl_blas": [True, False],
        "sycl_lapack": [True, False],
        "sycl_data_fitting": [True, False],
        "sycl_dft": [True, False],
        "sycl_rng": [True, False],
        "sycl_sparse": [True, False],
        "sycl_stats": [True, False],
        "sycl_vm": [True, False],
        "sycl_distributed_dft": [True, False],
    }
    default_options = {
        "shared": True,
        "interface": "lp64",
        "sdl": True,
        "interface_type": "intel",
        "threading": "tbb",
        "blas95": False,
        "lapack95": False,
        "sycl": False,
        "omp_offload": True,
        "blacs": False,
        "mpi": "intelmpi",
        "compatibility_headers": True,
        # SYCL submodules
        "sycl_blas": True,
        "sycl_lapack": True,
        "sycl_data_fitting": True,
        "sycl_dft": True,
        "sycl_rng": True,
        "sycl_sparse": True,
        "sycl_stats": True,
        "sycl_vm": True,
        "sycl_distributed_dft": True,
    }
    options_description = {
        "interface": "GNU or Intel interface to use",
        "sdl": "Use Single Dynamic Library interface for CMake targets",
        "interface_type": "Intel or GNU Fortran interface for CMake targets",
        "threading": "Threading layer for CMake targets",
        "blas95": "Add blas95 to MKL::MKL",
        "lapack95": "Add lapack95 to MKL::MKL",
        "sycl": "Include SYCL support. Requires intel-cc.",
        "omp_offload": "Add OpenMP offloading support to the main MKL::MKL target. Requires SYCL support.",
        "blacs": "Export BLACS, SCALAPACK and CDFT targets",
        "mpi": "BLACS MPI interface to use",
    }
    provides = ["mkl"]

    @property
    def extension_properties(self):
        if self.settings.os == "Windows" and self.options.interface_type == "intel":
            name_mangling = "upper_no_underscore"
        else:
            name_mangling = "lower_underscore"
        return {"fortran_name_mangling": name_mangling}

    @cached_property
    def _packages(self):
        with open(os.path.join(self.recipe_folder, "sources", f"{self.version}.yml")) as f:
            return yaml.safe_load(f)[str(self.settings.os)]

    @property
    def _sycl_domains(self):
        return ["blas", "lapack", "data_fitting", "dft", "rng", "sparse", "stats", "vm"]

    def export(self):
        copy(self, f"{self.version}.yml", os.path.join(self.recipe_folder, "sources"), os.path.join(self.export_folder, "sources"))

    def config_options(self):
        if self.settings.os != "Windows":
            # static is not supported due to Conan's inability to handle circular library dependencies
            del self.options.shared
            self.package_type = "shared-library"
        if self.settings.compiler == "intel-cc":
            self.options.interface = "ilp64"
            self.options.threading = "intel"
            self.options.sycl = True
        else:
            del self.options.omp_offload
        if Version(self.version) < "2025.2.0" or self.settings.os == "Windows":
            del self.options.sycl_distributed_dft

    def configure(self):
        if not self.options.get_safe("shared", True):
            del self.options.sdl
        if not self.options.blacs:
            del self.options.mpi
        else:
            self.provides = ["mkl", "blacs", "scalapack"]
        if not self.options.sycl or self.options.get_safe("sdl"):
            self.options.rm_safe("omp_offload")
        if not self.options.sycl:
            for opt, _ in list(self.options.items()):
                if opt.startswith("sycl_"):
                    self.options.rm_safe(opt)
        elif self.options.get_safe("sycl_distributed_dft"):
            self.options.sycl_dft.value = True

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type
        # Only the `interface` and `sycl` options matter for the package ID.
        # The optional components are always packaged (since they are relatively small),
        # but only enabled in package_info depending on the option values.
        # This also allows the SDL library (mkl_rt) to pick a suitable interface at runtime.
        for opt in ["sdl", "interface_type", "threading", "blas95", "lapack95", "omp_offload", "blacs", "mpi"]:
            self.info.options.rm_safe(opt)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.threading == "tbb":
            # Requires libonetbb.so.12
            self.requires("onetbb/[>=2021]")
        elif self.options.threading == "intel":
            v = Version(self.version)
            self.requires(f"intel-openmp/[~{v.major}.{v.minor}]", transitive_libs=True)
        if self.options.sycl:
            v = Version(self.version)
            self.requires(f"intel-dpcpp-sycl/[~{v.major}.{v.minor}]")
            self.requires(f"intel-opencl/[~{v.major}.{v.minor}]")
        if self.options.blacs or self.options.get_safe("sycl_distributed_dft"):
            if self.options.mpi == "intelmpi" or self.options.get_safe("sycl_distributed_dft"):
                self.requires("intelmpi/[^2021.18]", transitive_headers=True, transitive_libs=True)
            else:
                self.requires("openmpi/[>=4 <6]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ["FreeBSD", "Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration("Only x86_64 architecture is supported")
        if self.settings.compiler not in ["intel-cc", "clang"]:
            if self.options.sycl:
                raise ConanInvalidConfiguration(f"{self.settings.compiler} does not support SYCL.")
        if self.options.threading == "gnu" and self.settings.compiler not in ["gcc", "clang"]:
            raise ConanInvalidConfiguration("threading=gnu option is only available with GCC or Clang compilers.")
        if self.settings.os == "Windows" and self.options.blacs and self.options.mpi != "intelmpi":
            raise ConanInvalidConfiguration("Only Intel MPI is supported by BLACS on Windows")
        if self.options.get_safe("sycl_distributed_dft") and self.options.blacs and self.options.mpi != "intelmpi":
            raise ConanInvalidConfiguration("SYCL distributed DFT requires Intel -o mpi=intelmpi")

    def _get_pypi_package(self, name):
        get(self, **self._packages[name], destination=self.build_folder, strip_root=True)

    def build(self):
        self._get_pypi_package("mkl-devel")
        self._get_pypi_package("mkl-include")
        if self.options.get_safe("shared", True):
            self._get_pypi_package("mkl")
        else:
            self._get_pypi_package("mkl-static")

        if self.options.sycl:
            if not self.options.get_safe("shared", True) or self.settings.os == "Windows" or Version(self.version) < "2025.2.0":
                # provides a monolithic libmkl_sycl.a
                self._get_pypi_package("mkl-devel-dpcpp")
            if Version(self.version) >= "2025.2.0":
                self._get_pypi_package("onemkl-sycl-include")
            if self.options.sycl_blas:
                self._get_pypi_package("onemkl-sycl-blas")
            if self.options.sycl_lapack:
                self._get_pypi_package("onemkl-sycl-lapack")
            if self.options.sycl_data_fitting:
                self._get_pypi_package("onemkl-sycl-datafitting")
            if self.options.sycl_dft:
                self._get_pypi_package("onemkl-sycl-dft")
            if self.options.sycl_rng:
                self._get_pypi_package("onemkl-sycl-rng")
            if self.options.sycl_sparse:
                self._get_pypi_package("onemkl-sycl-sparse")
            if self.options.sycl_stats:
                self._get_pypi_package("onemkl-sycl-stats")
            if self.options.sycl_vm:
                self._get_pypi_package("onemkl-sycl-vm")
            if self.options.get_safe("sycl_distributed_dft"):
                if self.options.get_safe("shared", True):
                    self._get_pypi_package("onemkl-sycl-distributed-dft")
                else:
                    self._get_pypi_package("onemkl-devel-sycl-distributed-dft")

        if self.settings.os == "Windows":
            move_folder_contents(self, os.path.join(self.build_folder, "data", "Library"), self.source_folder)
            copy(self, "*", os.path.join(self.build_folder, "data"), self.source_folder)
        else:
            move_folder_contents(self, os.path.join(self.build_folder, "data"), self.source_folder)

    def package(self):
        copy(self, "LICENSE.txt", self.build_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "share/doc/mkl/licensing"), os.path.join(self.package_folder, "licenses"))

        mkdir(self, os.path.join(self.package_folder, "include"))
        mkdir(self, os.path.join(self.package_folder, "lib"))
        move_folder_contents(self, os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        move_folder_contents(self, os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
        if self.settings.os == "Windows" and self.options.get_safe("shared", True):
            mkdir(self, os.path.join(self.package_folder, "bin"))
            move_folder_contents(self, os.path.join(self.source_folder, "bin"), os.path.join(self.package_folder, "bin"))

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        # Keep only the libraries for the selected interface.
        # Could theoretically package both, but the other interface is just a gigabyte of dead weight.
        if self.options.interface == "ilp64":
            rm(self, "*_lp64*", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*_ilp64*", os.path.join(self.package_folder, "lib"))

        # Remove all non-runtime libraries that don't match shared=True/False
        if self.options.get_safe("shared", True):
            rm(self, "*.a", os.path.join(self.package_folder, "lib"), excludes=["*blas95*", "*lapack95*"])
        else:
            rm(self, "libmkl_rt.so*", os.path.join(self.package_folder, "lib"))
            for static_lib in Path(self.package_folder, "lib").glob("*.a"):
                if static_lib.with_suffix(".so").exists():
                    rm(self, f"{static_lib.stem}.so*", os.path.join(self.package_folder, "lib"))

        # Restore symlinks
        if self.settings.os in ["Linux", "FreeBSD"]:
            for f in Path(self.package_folder, "lib").glob("*.so.*"):
                Path(str(f).rsplit(".so", 1)[0] + ".so").symlink_to(f.name)

        if self.options.sycl and self.settings.os in ["Linux", "FreeBSD"]:
            # Create a linker script libmkl_sycl.so file that is otherwise provided by mkl-devel-dpcpp
            ldflags = [f"-lmkl_sycl_{domain}" for domain in self._sycl_domains if self.options.get_safe(f"sycl_{domain}")]
            save(self, os.path.join(self.package_folder, "lib", "libmkl_sycl.so"), f"INPUT({' '.join(ldflags)})\n")

        if self.options.sycl and self.settings.os == "Windows":
            if self.options.shared:
                rm(self, "mkl_sycl.lib", os.path.join(self.package_folder, "lib"))
            else:
                rm(self, "mkl_sycl_*_dll.lib", os.path.join(self.package_folder, "lib"))

        if self.options.compatibility_headers:
            save(self, os.path.join(self.package_folder, "include", "blas.h"), '#include "mkl_blas.h"\n')
            save(self, os.path.join(self.package_folder, "include", "cblas.h"), '#include "mkl_cblas.h"\n')
            save(self, os.path.join(self.package_folder, "include", "lapack.h"), '#include "mkl_lapack.h"\n')
            save(self, os.path.join(self.package_folder, "include", "lapacke.h"), '#include "mkl_lapacke.h"\n')

    @cached_property
    def _mkl_lib(self):
        threading_component = {
            "sequential": "seq",
            "tbb": "tbb",
            "intel": "iomp",
            "gnu": "gomp",
        }[self.options.threading.value]
        return f"mkl-{threading_component}"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "MKL")
        mkl_comp = self.cpp_info.components["mkl"]
        mkl_comp.set_property("cmake_target_name", "MKL::MKL")
        mkl_comp.set_property("pkg_config_name", "mkl")  # unofficial

        if self.options.get_safe("sdl"):
            mkl_comp.requires = ["mkl-sdl"]
        else:
            mkl_comp.requires = [self._mkl_lib]
        if self.options.blas95:
            mkl_comp.requires.append("blas95")
        if self.options.lapack95:
            mkl_comp.requires.append("lapack95")

        interface = self.options.interface.value
        suffix = "_dll" if self.settings.os == "Windows" and self.options.get_safe("shared", True) else ""

        # Single Dynamic Library (SDL) interface
        if self.options.get_safe("sdl"):
            self.cpp_info.components["mkl-sdl"].set_property("pkg_config_name", "mkl-sdl")
            self.cpp_info.components["mkl-sdl"].libs = ["mkl_rt"]
            if interface == "ilp64":
                self.cpp_info.components["mkl-sdl"].defines = ["MKL_ILP64"]
            # Configure the default interface via env vars
            # https://www.intel.com/content/www/us/en/docs/onemkl/developer-guide-linux/2025-1/dynamic-select-the-interface-and-threading-layer.html
            sdl_interface = interface.upper()
            if self.options.interface_type == "gf":
                sdl_interface = f"GNU,{sdl_interface}"
            self.runenv_info.define("MKL_INTERFACE_LAYER", sdl_interface)
            self.runenv_info.define("MKL_THREADING_LAYER", self.options.threading.value.upper())

        # Core library
        self.cpp_info.components["mkl-core"].libs = [f"mkl_core{suffix}"]
        if self.settings.os in ["Linux", "FreeBSD"] and not self.options.get_safe("shared", True):
            self.cpp_info.components["mkl-core"].system_libs = ["pthread", "m", "dl"]
        if not is_msvc(self) and self.options.get_safe("shared", True) and not self.options.sdl:
            # Hacky fix to handle circular dependencies between the shared libraries
            self.cpp_info.components["mkl-core"].sharedlinkflags = ["-Wl,--start-group"]
            self.cpp_info.components["mkl-core"].exelinkflags = ["-Wl,--start-group"]
            self.cpp_info.components["mkl-core"].system_libs.append("-Wl,--end-group")
        if interface == "ilp64":
            self.cpp_info.components["mkl-core"].defines = ["MKL_ILP64"]

        # Interface libraries
        interface_lib = f"mkl-{self.options.interface_type}"
        linkage = "dynamic" if self.options.get_safe("shared", True) else "static"
        if self.options.interface_type == "gf":
            self.cpp_info.components["mkl-gf"].libs = [f"mkl_gf_{interface}{suffix}"]
            self.cpp_info.components["mkl-gf"].requires = ["mkl-core"]
        elif self.options.interface_type == "intel":
            self.cpp_info.components["mkl-intel"].libs = [f"mkl_intel_{interface}{suffix}"]
            self.cpp_info.components["mkl-intel"].requires = ["mkl-core"]

        # Threading backend libraries
        if self.options.threading == "sequential":
            self.cpp_info.components["mkl-seq"].set_property("pkg_config_name", f"mkl-{linkage}-{interface}-seq")
            self.cpp_info.components["mkl-seq"].libs = [f"mkl_sequential{suffix}"]
            self.cpp_info.components["mkl-seq"].requires = [interface_lib]

        if self.options.threading == "tbb":
            self.cpp_info.components["mkl-tbb"].set_property("pkg_config_name", f"mkl-{linkage}-{interface}-tbb")
            self.cpp_info.components["mkl-tbb"].libs = [f"mkl_tbb_thread{suffix}"]
            self.cpp_info.components["mkl-tbb"].requires = [interface_lib, "onetbb::onetbb"]

        if self.options.threading == "gnu":
            self.cpp_info.components["mkl-gomp"].set_property("pkg_config_name", f"mkl-{linkage}-{interface}-gomp")
            self.cpp_info.components["mkl-gomp"].libs = ["mkl_gnu_thread"]
            self.cpp_info.components["mkl-gomp"].system_libs = ["gomp"]
            self.cpp_info.components["mkl-gomp"].exelinkflags = ["-Wl,--no-as-needed"]
            self.cpp_info.components["mkl-gomp"].sharedlinkflags = ["-Wl,--no-as-needed"]
            self.cpp_info.components["mkl-gomp"].requires = [interface_lib]

        if self.options.threading == "intel":
            self.cpp_info.components["mkl-iomp"].set_property("pkg_config_name", f"mkl-{linkage}-{interface}-iomp")
            self.cpp_info.components["mkl-iomp"].libs = [f"mkl_intel_thread{suffix}"]
            self.cpp_info.components["mkl-iomp"].requires = [interface_lib, "intel-openmp::intel-openmp"]

        # Cluster libraries
        if self.options.blacs:
            self.cpp_info.components["cdft"].set_property("cmake_target_name", "MKL::MKL_CDFT")
            self.cpp_info.components["cdft"].libs = [f"mkl_cdft_core{suffix}"]
            self.cpp_info.components["cdft"].requires = [f"blacs-{self.options.mpi}"]

            self.cpp_info.components["scalapack"].set_property("cmake_target_name", "MKL::MKL_SCALAPACK")
            self.cpp_info.components["scalapack"].libs = [f"mkl_scalapack_{interface}{suffix}"]
            self.cpp_info.components["scalapack"].requires = [f"blacs-{self.options.mpi}"]

            self.cpp_info.components["blacs"].set_property("cmake_target_name", "MKL::MKL_BLACS")
            self.cpp_info.components["blacs"].requires = [f"blacs-{self.options.mpi}"]
            if self.options.mpi == "intelmpi":
                if self.settings.os == "Windows" and self.options.get_safe("shared", True):
                    self.cpp_info.components["blacs-intelmpi"].libs = [f"mkl_blacs_{interface}{suffix}"]
                    self.runenv_info.define("MKL_BLACS_MPI", "INTELMPI")
                else:
                    self.cpp_info.components["blacs-intelmpi"].libs = [f"mkl_blacs_intelmpi_{interface}{suffix}"]
                self.cpp_info.components["blacs-intelmpi"].requires = [self._mkl_lib, "intelmpi::mpi-c"]
            if self.options.mpi == "openmpi":
                self.cpp_info.components["blacs-openmpi"].libs = [f"mkl_blacs_openmpi_{interface}{suffix}"]
                self.cpp_info.components["blacs-openmpi"].requires = [self._mkl_lib, "openmpi::ompi-c"]

        # Fortran95 API libraries
        if self.options.blas95:
            self.cpp_info.components["blas95"].libs = [f"mkl_blas95_{interface}{suffix}"]
            self.cpp_info.components["blas95"].requires = [self._mkl_lib]
        if self.options.lapack95:
            self.cpp_info.components["lapack95"].libs = [f"mkl_lapack95_{interface}{suffix}"]
            self.cpp_info.components["lapack95"].requires = [self._mkl_lib]

        # SYCL support
        if self.options.sycl:
            sycl_comp = self.cpp_info.components["mkl-sycl"]
            sycl_comp.set_property("cmake_target_name", "MKL::MKL_SYCL")
            if not self.options.get_safe("shared", True):
                sycl_comp.libs = ["mkl_sycl"]
            sycl_comp.requires = [
                self._mkl_lib,
                "intel-dpcpp-sycl::intel-dpcpp-sycl",
                "intel-opencl::intel-opencl",
            ]

            sycl_comp.cflags = ["-fsycl"]
            sycl_comp.cxxflags = ["-fsycl"]
            sycl_link_flags = ["-fsycl", "-Wl,-export-dynamic"]
            if not self.options.get_safe("shared", True):
                if self.settings.os == "Windows":
                    sycl_link_flags.append("-fsycl-device-code-split:per_kernel")
                else:
                    sycl_link_flags.append("-fsycl-device-code-split=per_kernel")
            sycl_comp.sharedlinkflags.extend(sycl_link_flags)
            sycl_comp.exelinkflags.extend(sycl_link_flags)

            for domain in self._sycl_domains:
                if not self.options.get_safe(f"sycl_{domain}"):
                    continue
                component_name = f"mkl-sycl-{domain}"
                comp = self.cpp_info.components[component_name]
                comp.set_property("cmake_target_name", f"MKL::MKL_SYCL::{domain.upper()}")
                if not self.options.get_safe("shared", True):
                    comp.requires = ["mkl-sycl"]
                else:
                    comp.libs = [f"mkl_sycl_{domain}{suffix}"]
                    comp.requires = [
                        self._mkl_lib,
                        "intel-dpcpp-sycl::intel-dpcpp-sycl",
                        "intel-opencl::intel-opencl",
                    ]
                    comp.cflags = ["-fsycl"]
                    comp.cxxflags = ["-fsycl"]
                    comp.sharedlinkflags = sycl_link_flags
                    comp.exelinkflags = sycl_link_flags
                    sycl_comp.requires.append(component_name)

            if self.options.get_safe("sycl_distributed_dft"):
                distributed_dft = self.cpp_info.components["mkl-sycl-distributed-dft"]
                distributed_dft.set_property("cmake_target_name", "MKL::MKL_SYCL_DISTRIBUTED_DFT")
                distributed_dft.libs = [f"mkl_sycl_distributed_dft{suffix}"]
                distributed_dft.requires = ["mkl-sycl-dft", "intelmpi::mpi-c"]

            if self.options.get_safe("omp_offload"):
                mkl_comp.requires.append("mkl-sycl")
                if self.settings.os == "Windows":
                    omp_cppflags = ["-Qiopenmp", "-Qopenmp-targets:spir64", "-Qopenmp-version:51"]
                    omp_ldflags = ["-Qiopenmp", "-Qopenmp-targets:spir64", "-fsycl"]
                else:
                    omp_cppflags = ["-fiopenmp", "-fopenmp-targets=spir64", "-fopenmp-version=51"]
                    omp_ldflags = ["-fiopenmp", "-fopenmp-targets=spir64", "-fsycl", "-Wl,-export-dynamic"]
                mkl_comp.cflags.extend(omp_cppflags)
                mkl_comp.cxxflags.extend(omp_cppflags)
                mkl_comp.sharedlinkflags.extend(omp_ldflags)
                mkl_comp.exelinkflags.extend(omp_ldflags)

        self.runenv_info.define_path("MKLROOT", self.package_folder)
        self.buildenv_info.define_path("MKLROOT", self.package_folder)
