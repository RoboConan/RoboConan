import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"

class LibmeshbConan(ConanFile):
    name = "libmeshb"
    description = "A library to handle the *.meshb file format."
    license = "MPL-2.0"
    homepage = "https://github.com/LoicMarechal/libMeshb"
    topics = ("3d", "mesh", "geometry")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_gmf_asio": [True, False],
        "enable_fortran": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_gmf_asio": False,
        "enable_fortran": False,
    }

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.with_gmf_asio
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def configure(self):
        # Windows shared build doesn't seems supported because code doesn't include dllexport
        # See https://www.kitware.com/create-dlls-on-windows-without-declspec-using-new-cmake-export-all-feature/
        if self.settings.os == "Windows":
            del self.options.shared
            self.package_type = "static-library"
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")
        if not self.options.enable_fortran:
            self.settings.rm_safe("fortran")

    def requirements(self):
        if self.options.enable_fortran:
            self.fortran.requires_runtime()

    def validate(self):
        if self.options.enable_fortran:
            self.fortran.validate_settings()

    def validate_build(self):
        if self.options.enable_fortran:
            self.fortran.validate_build()

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "add_subdirectory (examples)", "")
        replace_in_file(self, "CMakeLists.txt", "install (FILES LICENSE.txt copyright.txt DESTINATION share/libMeshb)", "")
        replace_in_file(self, "CMakeLists.txt", "install (DIRECTORY sample_meshes DESTINATION share/libMeshb)", "")
        replace_in_file(self, "CMakeLists.txt",
                        "check_language (Fortran)\nif(CMAKE_Fortran_COMPILER)",
                        "if(WITH_GMF_FORTRAN)\n  check_language (Fortran)\nendif()\n"
                        "if(WITH_GMF_FORTRAN AND CMAKE_Fortran_COMPILER)")
        replace_in_file(self, "sources/CMakeLists.txt",
                        "if(CMAKE_Fortran_COMPILER)",
                        "if(WITH_GMF_FORTRAN AND CMAKE_Fortran_COMPILER)")
        replace_in_file(self, "sources/CMakeLists.txt", "install(DIRECTORY ${CMAKE_Fortran_MODULE_DIRECTORY}/ DESTINATION include)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WITH_GMF_AIO"] = self.options.get_safe("with_gmf_asio", False)
        tc.variables["WITH_GMF_FORTRAN"] = self.options.enable_fortran
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libMeshb")
        self.cpp_info.set_property("cmake_target_name", "libMeshb::Meshb.7")
        self.cpp_info.libs = ["Meshb.7"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("rt")
            self.cpp_info.system_libs.append("m")
        if self.options.enable_fortran:
            self.fortran.add_runtime_to_cpp_info(self.cpp_info)
