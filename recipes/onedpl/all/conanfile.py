import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OneDplConan(ConanFile):
    name = "onedpl"
    description = ("OneDPL (Formerly Parallel STL) is an implementation of "
                   "the C++ standard library algorithms"
                   "with support for execution policies, as specified in "
                   "ISO/IEC 14882:2017 standard, commonly called C++17")
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/uxlfoundation/oneDPL"
    topics = ("stl", "parallelism")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "backend": ["tbb", "serial", "openmp", "dpcpp", "dpcpp_only"],
        "simd": [True, False],
    }
    default_options = {
        "backend": "tbb",
        "simd": True,
    }
    no_copy_source = True

    @property
    def _min_cppstd(self):
        if Version(self.version) < "2021.7.0":
            return 11
        return 17

    @property
    def _compilers_minimum_version(self):
        if Version(self.version) < "2021.7.0":
            return {}
        return {
            "gcc": "7",
            "clang": "6",
            "apple-clang": "10",
            "msvc": "191",
        }

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.backend in ["tbb", "dpcpp"]:
            self.requires("onetbb/[>=2021]", transitive_headers=True, transitive_libs=True)
        if self.options.backend == "openmp":
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.backend in ["dpcpp", "dpcpp_only"]:
            self.requires(f"intel-dpcpp-sycl/[~{self.settings.compiler.version}]", transitive_headers=True, transitive_libs=True)

    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)

        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
            )

        if self.settings.get_safe("compiler.libcxx") == "libstdc++":
            # https://stackoverflow.com/a/67924408/2997179
            raise ConanInvalidConfiguration("libstdc++ is not supported")

        if "2021.7" <= Version(self.version) < "2022" and is_msvc(self):
            raise ConanInvalidConfiguration(f"MSVC is not supported for {self.version} due to "
                                            "std::unary_function and std::binary_function being used")
        if self.options.backend in ["dpcpp", "dpcpp_only"]:
            if self.settings.compiler != "intel-cc" or self.settings.compiler.mode not in ["icx", "dpcpp"]:
                raise ConanInvalidConfiguration("The DPC++ backends require the IntelLLVM compiler")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "*", src=os.path.join(self.source_folder, "include"), dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.txt", src=os.path.join(self.source_folder, "licensing"), dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "oneDPL")
        self.cpp_info.set_property("cmake_target_name", "oneDPL")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        if self.options.backend == "tbb":
            self.cpp_info.defines.append("ONEDPL_USE_DPCPP_BACKEND=0")
        elif self.options.backend == "serial":
            self.cpp_info.defines.extend([
                "ONEDPL_USE_TBB_BACKEND=0",
                "ONEDPL_USE_DPCPP_BACKEND=0",
                "ONEDPL_USE_OPENMP_BACKEND=0",
            ])
        elif self.options.backend == "openmp":
            self.cpp_info.defines.extend([
                "ONEDPL_USE_TBB_BACKEND=0",
                "ONEDPL_USE_DPCPP_BACKEND=0",
                "ONEDPL_USE_OPENMP_BACKEND=1",
            ])
        elif self.options.backend == "dpcpp_only":
            self.cpp_info.defines.append("ONEDPL_USE_TBB_BACKEND=0")

        if self.options.backend in ["tbb", "dpcpp"] and self.settings.build_type == "Debug":
            self.cpp_info.defines.append("TBB_USE_DEBUG=1")
        if self.options.backend in ["dpcpp", "dpcpp_only"]:
            self.cpp_info.cxxflags.append("-fsycl")
            self.cpp_info.sharedlinkflags.append("-fsycl")
            self.cpp_info.exelinkflags.append("-fsycl")
        if self.options.simd and not is_msvc(self):
            self.cpp_info.cxxflags.append("-fopenmp-simd")
