import os
from functools import cached_property

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class CudaTileirasConan(ConanFile):
    name = "cuda-tileiras"
    description = "Compiler tools for CUDA Tile IR bytecode"
    license = "DocumentRef-LICENSE:LicenseRef-NVIDIA-CUDA-Toolkit-EULA"
    homepage = "https://docs.nvidia.com/cuda/tile-ir/"
    topics = ("cuda", "compiler", "tile-ir")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type", "cuda"

    python_requires = "conan-cuda/latest"

    @cached_property
    def cuda(self):
        return self.python_requires["conan-cuda"].module.Interface(self, enable_private=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # tileiras invokes the matching CUDA compiler backend (PTXAS and NVVM).
        # The nvcc package contains both for CUDA 13.
        self.cuda.requires("nvcc", run=True)

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type
        del self.info.settings.cuda.architectures
        self.info.settings.cuda.version = self.cuda.major

    def validate(self):
        self.cuda.validate_package("cuda_tileiras")

    def build(self):
        self.cuda.download_package("cuda_tileiras")

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "bin"), os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        cuda_root = self.dependencies["nvcc"].package_folder
        cuda_root_variable = "CUDA_PATH" if self.settings.os == "Windows" else "CUDA_HOME"
        self.runenv_info.define_path(cuda_root_variable, cuda_root)
