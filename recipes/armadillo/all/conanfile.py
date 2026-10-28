import os
import textwrap

from conan import ConanFile
from conan.tools.build import check_min_cppstd, valid_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.13"


class ArmadilloConan(ConanFile):
    name = "armadillo"
    description = "Armadillo is a high quality C++ library for linear algebra and scientific computing, aiming towards a good balance between speed and ease of use."
    license = "Apache-2.0"
    homepage = "http://arma.sourceforge.net"
    topics = ("linear algebra", "scientific computing", "matrix", "vector", "math", "hdf5", "header-only")
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {
        "header_only": [True, False],
        "shared": [True, False],
        "fPIC": [True, False],
        "with_blas": [True, False],
        "with_lapack": [True, False],
        "with_hdf5": [True, False],
        "with_superlu": [True, False],
        "with_arpack": [True, False],
        "with_openmp": [True, False],
    }
    default_options = {
        "header_only": True,
        "shared": False,
        "fPIC": True,
        "with_blas": True,
        "with_lapack": True,
        "with_hdf5": False,
        "with_superlu": False,
        "with_arpack": False,
        "with_openmp": True,
    }
    implements = ["auto_header_only", "auto_shared_fpic"]

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.header_only:
            self.options.rm_safe("fPIC")
            self.options.rm_safe("shared")
        elif self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_lapack:
            self.options.with_blas.value = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 14 if Version(self.version) >= 14 else 11)

    def requirements(self):
        if self.options.with_blas:
            self.requires("blas/latest", transitive_headers=True, transitive_libs=True)
        if self.options.with_lapack:
            self.requires("lapack/latest", transitive_headers=True, transitive_libs=True)
        if self.options.with_hdf5:
            self.requires("hdf5/[^1.8]", transitive_headers=True, transitive_libs=True)
        if self.options.with_arpack:
            self.requires("arpack-ng/[^3]", transitive_headers=True, transitive_libs=True)
        if self.options.with_superlu:
            self.requires("superlu/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        if Version(self.version) < 14:
            replace_in_file(self, "CMakeLists.txt",
                            "cmake_minimum_required(VERSION 2.8.12 FATAL_ERROR)",
                            "cmake_minimum_required(VERSION 3.5 FATAL_ERROR)")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD ", "# set(CMAKE_CXX_STANDARD ")
        template = textwrap.dedent("""\
            if(USE_@pkg@)
                find_package(@pkg@ REQUIRED)
            endif()
        """)
        save(self, "cmake_aux/Modules/ARMA_FindBLAS.cmake", template.replace("@pkg@", "BLAS"))
        save(self, "cmake_aux/Modules/ARMA_FindLAPACK.cmake", template.replace("@pkg@", "LAPACK"))
        save(self, "cmake_aux/Modules/ARMA_FindARPACK.cmake", template.replace("@pkg@", "ARPACK"))
        save(self, "cmake_aux/Modules/ARMA_FindSuperLU.cmake", template.replace("@pkg@", "SuperLU"))
        save(self, "cmake_aux/Modules/ARMA_FindATLAS.cmake", "")
        save(self, "cmake_aux/Modules/ARMA_FindFlexiBLAS.cmake", "")
        save(self, "cmake_aux/Modules/ARMA_FindMKL.cmake", "")
        save(self, "cmake_aux/Modules/ARMA_FindOpenBLAS.cmake", "")
        # Don't hard-code paths
        replace_in_file(self, "include/armadillo_bits/config.hpp.cmake", "${ARMA_SUPERLU_INCLUDE_DIR}/", "")
        replace_in_file(self, "include/armadillo_bits/config.hpp.cmake", "${CMAKE_REQUIRED_INCLUDES}", "")
        replace_in_file(self, "include/armadillo_bits/config.hpp.cmake", "${ARMA_LIBS}", "")

    def generate(self):
        tc = CMakeToolchain(self)
        if Version(self.version) >= 14:
            tc.cache_variables["HEADER_ONLY"] = self.options.header_only
        else:
            tc.cache_variables["ARMA_USE_WRAPPER"] = not self.options.header_only
        tc.cache_variables["STATIC_LIB"] = not self.options.get_safe("shared", False)
        tc.cache_variables["OPENBLAS_PROVIDES_LAPACK"] = False
        tc.cache_variables["ALLOW_FLEXIBLAS_LINUX"] = False
        tc.cache_variables["BUILD_SMOKE_TEST"] = False
        tc.cache_variables["USE_BLAS"] = self.options.with_blas
        tc.cache_variables["USE_LAPACK"] = self.options.with_lapack
        tc.cache_variables["USE_ARPACK"] = self.options.with_arpack
        tc.cache_variables["USE_SuperLU"] = self.options.with_superlu
        if self.options.with_blas:
            mangling = self.dependencies["blas"].extension_properties["fortran_name_mangling"]
            if mangling.startswith("upper_"):
                tc.preprocessor_definitions["ARMA_BLAS_CAPITALS"] = None
            if not mangling.endswith("no_underscore"):
                tc.preprocessor_definitions["ARMA_BLAS_UNDERSCORE"] = None
            if self.dependencies["blas"].options.interface == "ilp64":
                tc.preprocessor_definitions["ARMA_BLAS_LONG_LONG"] = None
                tc.preprocessor_definitions["ARMA_BLAS_64BIT_INT"] = None
                tc.preprocessor_definitions["ARMA_SUPERLU_64BIT_INT"] = None
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("arpack-ng", "cmake_file_name", "ARPACK")
        deps.set_property("superlu", "cmake_file_name", "SuperLU")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _get_arma_version_name(self):
        version_file = os.path.join(self.source_folder, "include", "armadillo_bits", "arma_version.hpp")
        with open(version_file, "r") as f:
            for line in f:
                if "ARMA_VERSION_NAME" in line:
                    return line.split("\"")[-2].strip()
        return ""

    def _create_cmake_module_variables(self, module_file):
        v = Version(self.version)
        content = textwrap.dedent(f"""\
            set(ARMADILLO_FOUND TRUE)
            if(DEFINED Armadillo_INCLUDE_DIRS)
                set(ARMADILLO_INCLUDE_DIRS ${{Armadillo_INCLUDE_DIRS}})
            endif()
            if(DEFINED Armadillo_LIBRARIES)
                set(ARMADILLO_LIBRARIES ${{Armadillo_LIBRARIES}})
            endif()
            set(ARMADILLO_VERSION_MAJOR "{v.major}")
            set(ARMADILLO_VERSION_MINOR "{v.minor}")
            set(ARMADILLO_VERSION_PATCH "{v.patch}")
            if(DEFINED Armadillo_VERSION_STRING)
                set(ARMADILLO_VERSION_STRING ${{Armadillo_VERSION_STRING}})
            else()
                set(ARMADILLO_VERSION_STRING "${{ARMADILLO_VERSION_MAJOR}}.${{ARMADILLO_VERSION_MINOR}}.${{ARMADILLO_VERSION_PATCH}}")
            endif()
            set(ARMADILLO_VERSION_NAME "{self._get_arma_version_name}")
        """)
        save(self, module_file, content)

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        self._create_cmake_module_variables(os.path.join(self.package_folder, "share/conan/armadillo-variables.cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "Armadillo")
        self.cpp_info.set_property("cmake_target_name", "armadillo")  # ArmadilloConfig.cmake
        self.cpp_info.set_property("cmake_target_aliases", ["Armadillo::Armadillo"])  # FindArmadillo.cmake
        self.cpp_info.set_property("cmake_config_version_compat", "AnyNewerVersion")
        self.cpp_info.set_property("cmake_build_modules", ["share/conan/armadillo-variables.cmake"])
        self.cpp_info.set_property("pkg_config_name", "armadillo")

        if self.options.header_only:
            self.cpp_info.libdirs = []
            self.cpp_info.bindirs = []
        else:
            self.cpp_info.libs = ["armadillo"]

        self.cpp_info.builddirs = ["share/conan"]

        if self.options.with_blas:
            mangling = self.dependencies["blas"].extension_properties["fortran_name_mangling"]
            if mangling.startswith("upper_"):
                self.cpp_info.defines.append("ARMA_BLAS_CAPITALS")
            if not mangling.endswith("no_underscore"):
                self.cpp_info.defines.append("ARMA_BLAS_UNDERSCORE")
            self.cpp_info.defines.append("ARMA_USE_FORTRAN_HIDDEN_ARGS")
            if self.dependencies["blas"].options.interface == "ilp64":
                self.cpp_info.defines.append("ARMA_BLAS_LONG_LONG")
                self.cpp_info.defines.append("ARMA_BLAS_64BIT_INT")
                self.cpp_info.defines.append("ARMA_SUPERLU_64BIT_INT")
            if self.dependencies["blas"].options.provider == "mkl":
                self.cpp_info.defines.append("ARMA_USE_MKL_ALLOC")

        if self.settings.build_type not in ["Debug", "RelWithDebInfo"]:
            self.cpp_info.defines.append("ARMA_NO_DEBUG")

        if valid_min_cppstd(self, 17):
            self.cpp_info.defines.append("ARMA_HAVE_CXX17")
        if valid_min_cppstd(self, 20):
            self.cpp_info.defines.append("ARMA_HAVE_CXX20")
        if valid_min_cppstd(self, 23):
            self.cpp_info.defines.append("ARMA_HAVE_CXX23")

        def _set_use_define(name, value):
            if value:
                self.cpp_info.defines.append(f"ARMA_USE_{name}")
            else:
                self.cpp_info.defines.append(f"ARMA_DONT_USE_{name}")

        _set_use_define("WRAPPER", not self.options.header_only)
        _set_use_define("HDF5", self.options.with_hdf5)
        _set_use_define("BLAS", self.options.with_blas)
        _set_use_define("LAPACK", self.options.with_lapack)
        _set_use_define("ARPACK", self.options.with_arpack)
        _set_use_define("SUPERLU", self.options.with_superlu)
        _set_use_define("OPENMP", self.options.with_openmp)
        _set_use_define("ATLAS", False)
