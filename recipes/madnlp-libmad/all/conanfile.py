import os
from functools import cached_property

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class MadNlpLibMadConan(ConanFile):
    name = "madnlp-libmad"
    description = "C interface library for the MadNLP and CCOpt Julia solvers"
    license = "MIT"
    homepage = "https://github.com/madsuite-org/libMad"
    topics = ("optimization", "nonlinear-optimization", "madnlp", "ccopt", "casadi", "pre-built")
    package_type = "shared-library"
    no_copy_source = True
    settings = "os", "arch", "compiler"
    options = {
        "with_cuda": [True, False],
    }
    default_options = {
        "with_cuda": False,
    }

    def config_options(self):
        if self.settings.os not in ["Linux", "Windows"]:
            self.options.rm_safe("with_cuda")

    def package_id(self):
        if self.info.settings.os != "Windows":
            del self.info.settings.compiler
        elif self.info.settings.compiler == "gcc":
            del self.info.settings.compiler.version

    def layout(self):
        basic_layout(self, src_folder="src")

    @cached_property
    def _download_info(self):
        platform = self.conan_data["sources"][self.version].get(str(self.settings.os), {})
        info = platform.get(str(self.settings.arch))
        if info and self.options.get_safe("with_cuda"):
            info = info.get("cuda")
        elif info:
            info = {key: value for key, value in info.items() if key != "cuda"}
        return info

    def validate(self):
        if not self._download_info:
            raise ConanInvalidConfiguration(f"{self.settings.os}/{self.settings.arch} is not supported")
        if self.settings.os == "Windows" and self.settings.compiler != "gcc":
            raise ConanInvalidConfiguration("The Windows release provides a MinGW import library")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["license"], destination="licenses", strip_root=True)

    def build(self):
        # Release assets vary by platform and CUDA support, while Conan source
        # folders are shared by every binary package of a recipe revision.
        get(self, **self._download_info, destination=self.build_folder, strip_root=True)

    def package(self):
        copy(self, "LICENSE", os.path.join(self.source_folder, "licenses"), os.path.join(self.package_folder, "licenses"))
        for directory in ["bin", "include", "lib", "share"]:
            copy(self, "*",
                 os.path.join(self.build_folder, directory),
                 os.path.join(self.package_folder, directory))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libmad")
        self.cpp_info.set_property("cmake_target_name", "libmad::libMad")
        self.cpp_info.libs = ["Mad"]
        if self.settings.os == "Windows":
            self.cpp_info.libdirs = ["bin"]
        self.runenv_info.define("JULIA_CUDA_USE_COMPAT", "false")
