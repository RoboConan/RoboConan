from functools import cached_property

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration

required_conan_version = ">=2.1"


class LapackConan(ConanFile):
    name = "lapack"
    version = "latest"
    description = "LAPACK meta-package for Conan"
    license = "MIT"
    homepage = "https://www.netlib.org/lapack/"
    topics = ("blas", "linear-algebra", "meta-package")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "provider": [
            "reference",
            "openblas",
            "mkl",
            "accelerate",
            "armpl",
            "nvpl",
            # TODO:
            # libblastrampoline
            # flexiblas
        ],
    }
    default_options = {
        "shared": False,
        "provider": "openblas",
    }

    @cached_property
    def _dep_name(self):
        provider = str(self.options.provider)
        return {
            "reference": "lapack-reference",
            "mkl": "onemkl",
            "nvpl": "nvpl_blas",
        }.get(provider, provider)

    def configure(self):
        if self.options.provider != "reference":
            self.options["blas"].provider = self.options.provider
        if self.options.provider in ["mkl", "nvpl", "accelerate"]:
            self.options.shared.value = True
        else:
            self.options[self._dep_name].shared = self.options.shared
        self.options["openblas"].build_lapack = self.options.provider == "openblas"

    def requirements(self):
        self.requires("blas/latest")
        if self.options.provider == "reference":
            self.requires("lapack-reference/[^3.12]")
        elif self.options.provider == "nvpl":
            self.requires("nvpl_lapack/[<1]")

    def package_id(self):
        self.info.settings.clear()
        self.info.requires["blas"].full_package_mode()

    @cached_property
    def _dependency(self):
        return self.dependencies[self._dep_name]

    def validate(self):
        if self.options.provider != "reference":
            if self.dependencies["blas"].options.provider != self.options.provider:
                raise ConanInvalidConfiguration(
                    "-o blas/latest:provider and -o lapack/latest:provider must match "
                    f"({self.dependencies['blas'].options.provider} != {self.options.provider})")
        if self.options.provider == "openblas" and not self.dependencies["openblas"].options.build_lapack:
            raise ConanInvalidConfiguration("-o openblas/*:build_lapack must be enabled")
        if self.options.provider not in ["mkl", "nvpl", "accelerate"]:
            if self._dependency.options.shared != self.options.shared:
                raise ConanInvalidConfiguration(f"-o {self._dependency.ref}:shared != {self.options.shared} value from -o {self.ref}:shared")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "LAPACK")
        self.cpp_info.set_property("cmake_target_name", "LAPACK::LAPACK")
        if self.options.provider != "reference":
            self.cpp_info.set_property("pkg_config_name", "lapack")

        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
