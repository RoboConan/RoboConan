import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMake, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"

class RotorConan(ConanFile):
    name = "rotor"
    description = "Event loop friendly C++ actor micro-framework, supervisable"
    license = "MIT"
    homepage = "https://github.com/basiliscos/cpp-rotor"
    topics = ("concurrency", "actor-framework", "actors", "actor-model", "erlang", "supervising", "supervisor")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "shared": [True, False],
        "enable_asio": [True, False],
        "enable_thread": [True, False],
        "multithreading": [True, False],  # enables multithreading support
        "enable_ev": [True, False],
        "enable_fltk": [True, False],
    }
    default_options = {
        "fPIC": True,
        "shared": False,
        "enable_asio": False,
        "enable_thread": False,
        "multithreading": True,
        "enable_ev": False,
        "enable_fltk": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if Version(self.version) < "0.30":
            del self.options.enable_fltk

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["boost"].with_date_time = True
        self.options["boost"].with_regex = True

    def requirements(self):
        self.requires("boost/[^1.71.0]", transitive_headers=True)
        if self.options.get_safe("enable_ev", False):
            self.requires("libev/[^4.33]")
        if self.options.get_safe("enable_fltk", False):
            self.requires("fltk/[^1.3.9]")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        v = Version(self.version)
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_BOOST_ASIO" if v < "0.34" else "ROTOR_BUILD_ASIO"] = self.options.enable_asio
        tc.cache_variables["BUILD_THREAD" if v < "0.34" else "ROTOR_BUILD_THREAD"] = self.options.enable_thread
        tc.cache_variables["BUILD_THREAD_UNSAFE" if v < "0.34" else "ROTOR_BUILD_THREAD_UNSAFE"] = not self.options.multithreading
        tc.cache_variables["BUILD_TESTING" if v < "0.34" else "ROTOR_BUILD_TESTS"] = False
        tc.cache_variables["BUILD_EV" if v < "0.34" else "ROTOR_BUILD_EV"] = self.options.enable_ev
        if v >= "0.30":
            tc.cache_variables["BUILD_FLTK" if v < "0.34" else "ROTOR_BUILD_FLTK"] = self.options.enable_fltk
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.components["core"].libs = ["rotor"]
        self.cpp_info.components["core"].requires = ["boost::date_time", "boost::regex"]

        if not self.options.multithreading:
            v = Version(self.version)
            self.cpp_info.components["core"].defines.append("BUILD_THREAD_UNSAFE" if v < "0.34" else "ROTOR_BUILD_THREAD_UNSAFE")

        if self.options.enable_asio:
            self.cpp_info.components["asio"].libs = ["rotor_asio"]
            self.cpp_info.components["asio"].requires = ["core"]
            if self.settings.os == "Windows":
                self.cpp_info.components["asio"].system_libs = ["ws2_32"]

        if self.options.enable_thread:
            self.cpp_info.components["thread"].libs = ["rotor_thread"]
            self.cpp_info.components["thread"].requires = ["core"]

        if self.options.get_safe("enable_ev", False):
            self.cpp_info.components["ev"].libs = ["rotor_ev"]
            self.cpp_info.components["ev"].requires = ["core", "libev::libev"]

        if self.options.get_safe("enable_fltk", False):
            self.cpp_info.components["fltk"].libs = ["rotor_fltk"]
            self.cpp_info.components["fltk"].requires = ["core", "fltk::fltk"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["core"].system_libs.append("m")
