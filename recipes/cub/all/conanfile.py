import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class CubConan(ConanFile):
    name = "cub"
    description = "Cooperative primitives for CUDA C++"
    license = "BSD 3-Clause"
    homepage = "https://github.com/NVIDIA/cccl/tree/main/cub"
    topics = ("algorithms", "cuda", "gpu", "nvidia", "nvidia-hpc-sdk", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def requirements(self):
        if Version(self.version) >= "2.0":
            self.requires(f"libcudacxx/{self.version}")

    def validate(self):
        check_min_cppstd(self, 14)

    @property
    def _cmake_dir(self):
        if Version(self.version) >= "2.8":
            return os.path.join(self.source_folder, "lib/cmake/cub")
        elif Version(self.version) >= "2.2":
            return os.path.join(self.source_folder, "cub/cub/cmake")
        else:
            return os.path.join(self.source_folder, "cub/cmake")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        cmake_config = os.path.join(self._cmake_dir, "cub-config.cmake")
        replace_in_file(self, cmake_config,
                        "${_CUB_VERSION_INCLUDE_DIR}",
                        "${${CMAKE_FIND_PACKAGE_NAME}_INCLUDE_DIR}")
        replace_in_file(self, cmake_config,
                        "set(CUB_CONFIG",
                        "# set(CUB_CONFIG")
        replace_in_file(self, cmake_config,
                        "find_package_handle_standard_args(",
                        "# find_package_handle_standard_args(")

    def package(self):
        if Version(self.version) >= "2.2":
            copy(self, "LICENSE.TXT", os.path.join(self.source_folder, "cub"), os.path.join(self.package_folder, "licenses"))
            copy(self, "*", os.path.join(self.source_folder, "cub", "cub"), os.path.join(self.package_folder, "include", "cub"))
        else:
            copy(self, "LICENSE.TXT", self.source_folder, os.path.join(self.package_folder, "licenses"))
            copy(self, "*", os.path.join(self.source_folder, "cub"), os.path.join(self.package_folder, "include", "cub"))
        copy(self, "cub-config.cmake", self._cmake_dir, os.path.join(self.package_folder, "lib/cmake"))
        rename(self, os.path.join(self.package_folder, "lib/cmake/cub-config.cmake"),
               os.path.join(self.package_folder, "lib/cmake/cub-config-official.cmake"))

    def package_info(self):
        # Follows the naming conventions of the official CMake config file:
        # https://github.com/NVIDIA/cccl/blob/main/lib/cmake/cub/cub-config.cmake
        self.cpp_info.set_property("cmake_file_name", "cub")
        # Disable the default target.
        # CUB::CUB is created in the loaded .cmake module instead.
        self.cpp_info.set_property("cmake_target_name", "_cub_do_not_use")
        # The CMake module ensures that the include dir is exported as a non-SYSTEM include in CMake
        # https://github.com/NVIDIA/cccl/blob/v2.2.0/cub/lib/cmake/cub/cub-config.cmake#L11-L29
        self.cpp_info.set_property("cmake_build_modules", ["lib/cmake/cub-config-official.cmake"])
        self.cpp_info.set_property("system_package_version", self.version.split("-")[0])

        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.builddirs = ["lib/cmake"]

        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
