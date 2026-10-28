import os
from functools import cached_property

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class IntelDpcppConan(ConanFile):
    name = "intel-dpcpp"
    description = "Intel oneAPI DPC++/C++ Compiler"
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://www.intel.com/content/www/us/en/developer/tools/oneapi/dpc-compiler.html"
    topics = ("intel", "oneapi", "compiler", "sycl", "pre-built")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "debugger": [True, False],
        "dev_utilities": [True, False],
        "dpl": [True, False],
        "tbb": [True, False],
        "tcm": [True, False],
        "umf": [True, False],
    }
    default_options = {
        "debugger": False,
        "dev_utilities": False,
        "dpl": False,
        "tbb": False,
        "tcm": False,
        "umf": False,
    }

    upload_policy = "skip"
    build_policy = "missing"

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    @cached_property
    def _packages(self):
        with open(os.path.join(self.recipe_folder, "sources", f"{self.version}.yml")) as f:
            return yaml.safe_load(f)[str(self.settings.os)]

    def export(self):
        copy(self, f"{self.version}.yml", os.path.join(self.recipe_folder, "sources"),
             os.path.join(self.export_folder, "sources"))

    @property
    def _upstream_minor(self):
        return ".".join(str(self.version).split(".")[:2])

    @property
    def _target_settings(self):
        return self.settings_target or self.settings

    @property
    def _extracted_root(self):
        return os.path.join(self.build_folder, "extracted")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        version = self._upstream_minor
        self.requires(f"intel-opencl/[~{version}]")
        self.requires(f"intel-dpcpp-sycl/[~{version}]")
        self.requires(f"intel-openmp/[~{version}]")
        if self.options.dpl:
            self.requires("onedpl/[^2022.14]")
        if self.options.tbb:
            self.requires("onetbb/[^2023.1]")
        if self.options.tcm:
            self.requires("intel-tcmlib/[~1.6]")
        if self.options.umf:
            self.requires("umf/[~1.2]")

    def validate(self):
        if self.settings.os not in ["FreeBSD", "Linux"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration("Only x86_64 host architecture is supported")
        if self._target_settings.os != self.settings.os \
                or self._target_settings.arch != self.settings.arch:
            raise ConanInvalidConfiguration("The packaged Intel DPC++ compiler is not a cross compiler")
        if self.settings.compiler.libcxx != "libstdc++11":
            raise ConanInvalidConfiguration(
                "compiler.libcxx=libstdc++11 is required for compatibility with the compiler runtime libraries"
            )
        if self.options.dev_utilities and "intel-oneapi-dev-utilities" not in self._packages:
            raise ConanInvalidConfiguration(
                f"The developer utilities are not available for Intel DPC++ {self.version}"
            )

    def _extract_package(self, name, subdir, destination):
        package_file = os.path.join(self.build_folder, f"{name}.deb")
        download(self, **self._packages[name], filename=package_file)
        self._utils.extract_deb(package_file, destination, subdir)

    def build(self):
        compiler_root = f"opt/intel/oneapi/compiler/{self._upstream_minor}"
        # Intel splits tools and runtime files addressed relative to icpx
        # across the compiler runtime and OpenMP DEBs. Their graph packages
        # remain necessary for built applications, but cannot satisfy the
        # compiler driver's relative lookups.
        for package in [
            "intel-oneapi-dpcpp-cpp",
            "intel-oneapi-compiler-dpcpp-cpp-common",
            "intel-oneapi-compiler-dpcpp-cpp-runtime",
            "intel-oneapi-compiler-shared",
            "intel-oneapi-compiler-shared-common",
            "intel-oneapi-compiler-shared-runtime",
            "intel-oneapi-openmp",
        ]:
            self._extract_package(package, compiler_root, self._extracted_root)
        if self.options.debugger:
            self._extract_package(
                "intel-oneapi-dpcpp-debugger",
                f"opt/intel/oneapi/debugger/{self._upstream_minor}",
                os.path.join(self._extracted_root, "opt", "debugger"),
            )
        if self.options.dev_utilities:
            self._extract_package(
                "intel-oneapi-dev-utilities",
                f"opt/intel/oneapi/dev-utilities/{self._upstream_minor}",
                os.path.join(self._extracted_root, "opt", "dev-utilities"),
            )

    def package(self):
        move_folder_contents(self, self._extracted_root, self.package_folder)
        license_dir = os.path.join(self.package_folder, "share", "doc", "compiler", "licensing", "c")
        copy(self, "LICENSE", license_dir, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "third-party-programs.txt", license_dir,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        rmdir(self, os.path.join(self.package_folder, ".toolkit_linking_tool"))
        rmdir(self, os.path.join(self.package_folder, "env"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))

        save(self, os.path.join(self.package_folder, "setvars.sh"), "#!/bin/sh\n")
        os.chmod(os.path.join(self.package_folder, "setvars.sh"), 0o755)

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin", os.path.join("bin", "compiler")]
        self.cpp_info.resdirs = ["share", "opt"]

        compiler = os.path.join(self.package_folder, "bin", "icx")
        compiler_cxx = os.path.join(self.package_folder, "bin", "icpx")
        self.buildenv_info.define_path("CC", compiler)
        self.buildenv_info.define_path("CXX", compiler_cxx)
        self.buildenv_info.prepend_path(
            "NLSPATH", os.path.join(self.package_folder, "lib", "compiler", "locale", "%l_%t", "%N")
        )

        if self.options.umf:
            self.buildenv_info.define_path("UMF_ROOT", self.dependencies["umf"].package_folder)
        if self.options.tcm:
            self.buildenv_info.define_path("TCM_ROOT", self.dependencies["intel-tcmlib"].package_folder)
        if self.options.dpl:
            self.buildenv_info.define_path("DPL_ROOT", self.dependencies["onedpl"].package_folder)
        if self.options.tbb:
            self.buildenv_info.define_path("TBBROOT", self.dependencies["onetbb"].package_folder)
        if self.options.debugger:
            self.buildenv_info.define_path("INTEL_PYTHONHOME", os.path.join(self.package_folder, "opt", "debugger"))
            self.cpp_info.bindirs.append(os.path.join("opt", "debugger", "bin"))
            self.buildenv_info.prepend_path("GDB_INFO", os.path.join(self.package_folder, "share", "info"))

        self.conf_info.update("tools.build:compiler_executables", {
            "c": compiler,
            "cpp": compiler_cxx,
        })
        self.conf_info.define_path("tools.intel:installation_path", self.package_folder)
