import os
from functools import cached_property

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class NvplBlasConan(ConanFile):
    name = "nvpl_blas"
    description = ("NVPL BLAS (NVIDIA Performance Libraries BLAS) is part of NVIDIA Performance Libraries"
                   " that provides standard Fortran 77 BLAS APIs as well as C (CBLAS).")
    license = "DocumentRef-LICENSE:LicenseRef-NVIDIA-Software-License-Agreement"
    homepage = "https://docs.nvidia.com/nvpl"
    topics = ("cuda", "nvpl", "blas", "linear-algebra")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "interface": ["lp64", "ilp64"],
        "threading": ["seq", "omp"],
        "compatibility_headers": [True, False],
    }
    default_options = {
        "interface": "lp64",
        "threading": "omp",
        "compatibility_headers": True,
    }

    python_requires = "conan-cuda/latest"

    @cached_property
    def cuda(self):
        return self.python_requires["conan-cuda"].module.Interface(self, enable_private=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("NVPL libraries are only supported on Linux")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("NVPL libraries are only supported on armv8")

    def build(self):
        self.cuda.download_package("nvpl_blas", platform_id="linux-sbsa")

    @property
    def _backend_name(self):
        name = f"nvpl_blas_{self.options.interface}"
        if self.options.threading == "omp":
            name += "_gomp"
        else:
            name += "_seq"
        return name

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        copy(self, f"*_core.so*", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
        copy(self, f"*{self._backend_name}*.so*", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
        if self.options.compatibility_headers:
            save(self, os.path.join(self.package_folder, "include", "cblas.h"), '#include "nvpl_blas_cblas.h"\n')
            save(self, os.path.join(self.package_folder, "include", "f77blas.h"),
                 '#include "nvpl_blas_f77_blas.h"\ntypedef nvpl_int_t blasint;\n')

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "nvpl_blas")
        # Unofficial target
        self.cpp_info.set_property("cmake_target_name", "nvpl::nvpl_blas")

        def _add_component(name):
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", name)
            component.set_property("cmake_target_aliases", [name.replace("nvpl_", "nvpl::")])
            component.libs = [name]
            if "ilp64" in name:
                component.defines = ["NVPL_ILP64"]
            if name != "nvpl_blas_core":
                component.requires = ["nvpl_blas_core"]

        _add_component("nvpl_blas_core")
        _add_component(self._backend_name)
