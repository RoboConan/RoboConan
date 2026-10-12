import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class ThrustConan(ConanFile):
    name = "thrust"
    description = "Thrust is a parallel algorithms library which resembles the C++ Standard Template Library (STL)."
    license = "Apache-2.0 AND BSL-1.0 AND BSD-2-Clause"
    topics = ("parallel", "stl", "cuda", "gpgpu", "header-only")
    homepage = "https://nvidia.github.io/thrust/"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"cub/{self.version}")

    def package_id(self):
        self.info.clear()

    @property
    def _cmake_dir(self):
        if Version(self.version) >= "2.8":
            return os.path.join(self.source_folder, "lib/cmake/thrust")
        elif Version(self.version) >= "2.2":
            return os.path.join(self.source_folder, "thrust/thrust/cmake")
        else:
            return os.path.join(self.source_folder, "thrust/cmake")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        cmake_config = os.path.join(self._cmake_dir, "thrust-config.cmake")
        if Version(self.version) < "3.2":
            replace_in_file(self, cmake_config,
                            "find_package(CUB ",
                            'message(TRACE "find_package(CUB" ')
        replace_in_file(self, cmake_config,
                        "${_THRUST_VERSION_INCLUDE_DIR}",
                        "${${CMAKE_FIND_PACKAGE_NAME}_INCLUDE_DIR}")
        replace_in_file(self, cmake_config,
                        "set(Thrust_CONFIG",
                        "# set(Thrust_CONFIG")
        replace_in_file(self, cmake_config,
                        "find_package_handle_standard_args(",
                        "# find_package_handle_standard_args(")
        if self.version == "2.1.0":
            replace_in_file(self, cmake_config,
                            "set(thrust_libcudacxx_version 1.8.0)",
                            f"set(thrust_libcudacxx_version {self.version})")

    def package(self):
        if Version(self.version) >= "2.2":
            copy(self, "LICENSE", os.path.join(self.source_folder, "thrust"), os.path.join(self.package_folder, "licenses"))
            copy(self, "*", os.path.join(self.source_folder, "thrust", "thrust"), os.path.join(self.package_folder, "include", "thrust"))
        else:
            copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
            copy(self, "*", os.path.join(self.source_folder, "thrust"), os.path.join(self.package_folder, "include", "thrust"))
        copy(self, "thrust-config.cmake", self._cmake_dir, os.path.join(self.package_folder, "lib/cmake"))
        rename(self, os.path.join(self.package_folder, "lib/cmake/thrust-config.cmake"),
                     os.path.join(self.package_folder, "lib/cmake/thrust-config-official.cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Thrust")
        # Disable the default target.
        # Thrust::Thrust is created in the loaded .cmake module instead.
        # https://github.com/NVIDIA/cccl/blob/main/lib/cmake/thrust/thrust-config.cmake
        self.cpp_info.set_property("cmake_target_name", "_thrust_do_not_use")
        self.cpp_info.set_property("cmake_build_modules", ["lib/cmake/thrust-config-official.cmake"])
        self.cpp_info.set_property("system_package_version", self.version.split("-")[0])

        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.builddirs = ["lib/cmake"]
