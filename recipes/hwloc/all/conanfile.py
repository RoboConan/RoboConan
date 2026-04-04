import os

from conan import ConanFile
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, AutotoolsDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class HwlocConan(ConanFile):
    name = "hwloc"
    description = "Portable Hardware Locality (hwloc)"
    license = "BSD-3-Clause"
    homepage = "https://www.open-mpi.org/projects/hwloc/"
    topics = ("hardware", "topology")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "with_cairo": [True, False],
        "with_libxml2": [True, False],
        "with_cuda": [True, False],
        "with_opencl": [True, False],
        "with_oneapi": [True, False],
        "with_pci": [True, False],
        "with_udev": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": False,
        "with_cairo": False,  # only needed for topology visualization tools
        "with_libxml2": False,  # uses an internal simpler writer/parser if disabled
        "with_cuda": False,
        "with_opencl": False,
        "with_oneapi": False,
        "with_pci": False,
        "with_udev": False,  # uses an internal udev parser if disabled
    }
    languages = ["C"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def configure(self):
        if not self.options.with_cuda:
            del self.settings.cuda
        else:
            self.options.with_opencl.value = True
        if not self.options.tools:
            del self.options.with_cairo

    def requirements(self):
        if self.options.get_safe("with_cairo"):
            self.requires("cairo/[^1.17.8]")
        if self.options.with_libxml2:
            self.requires("libxml2/[^2.12.5]")
        if self.options.with_cuda:
            self.cuda.requires("cudart")
            self.cuda.requires("nvml-stubs")
        if self.options.with_opencl:
            self.requires("opencl-icd-loader/[*]")
        if self.options.with_oneapi:
            self.requires("level-zero/[^1.17.39]")
        if self.options.with_pci:
            self.requires("libpciaccess/[>=0.17 <1]")
        if self.options.with_udev:
            self.requires("libudev/[^255]")

    def validate(self):
        if self.options.with_cuda:
            self.cuda.validate_settings()

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        save(self, "doc/Makefile.in", "all:;\ninstall:;\n")

    def layout(self):
        if self.settings.os == "Windows":
            cmake_layout(self, src_folder="src")
        else:
            basic_layout(self, src_folder="src")

    def generate(self):
        if self.settings.os == "Windows":
            tc = CMakeToolchain(self)
            tc.cache_variables["HWLOC_ENABLE_TESTING"] = False
            tc.cache_variables["HWLOC_SKIP_LSTOPO"] = True
            tc.cache_variables["HWLOC_SKIP_TOOLS"] = True
            tc.cache_variables["HWLOC_SKIP_INCLUDES"] = False
            tc.cache_variables["HWLOC_WITH_OPENCL"] = False
            tc.cache_variables["HWLOC_WITH_CUDA"] = self.options.with_cuda
            tc.cache_variables["HWLOC_WITH_LIBXML2"] = self.options.with_libxml2
            tc.generate()
            deps = CMakeDeps(self)
            deps.generate()
        else:
            enable_disable = lambda opt, val: f"--enable-{opt}" if val else f"--disable-{opt}"
            tc = AutotoolsToolchain(self)
            tc.configure_args.extend([
                enable_disable("libxml2", self.options.with_libxml2),
                enable_disable("cairo", self.options.get_safe("with_cairo")),
                enable_disable("cuda", self.options.with_cuda),
                enable_disable("nvml", self.options.with_cuda),
                enable_disable("opencl", self.options.with_opencl),
                enable_disable("rsmi", self.options.get_safe("with_rocm")),
                enable_disable("levelzero", self.options.with_oneapi),
                enable_disable("pci", self.options.with_pci),
                enable_disable("libudev", self.options.with_udev),
                enable_disable("gl", False),  # Only for NVIDIA devices, requires NVCtrl library from nvidia-settings
                enable_disable("plugins", False),  # Keep it simple with a monolithic build
                enable_disable("doxygen", False),
                enable_disable("readme", False),
            ])
            tc.generate()
            deps = PkgConfigDeps(self)
            deps.generate()
            if self.options.with_cuda:
                tc = AutotoolsDeps(self)
                tc.generate()

    def build(self):
        if self.settings.os == "Windows":
            cmake = CMake(self)
            cmake.configure(build_script_folder="contrib/windows-cmake")
            cmake.build()
        else:
            if not self.options.tools:
                save(self, os.path.join(self.source_folder, "utils", "Makefile.in"), "all:;\ninstall:;\n")
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "Windows":
            cmake = CMake(self)
            cmake.install()
            rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        else:
            autotools = Autotools(self)
            autotools.install()
            rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
            fix_apple_shared_install_name(self)
            if not self.options.tools:
                rmdir(self, os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "hwloc")
        self.cpp_info.libs = ["hwloc"]
        if is_apple_os(self):
            self.cpp_info.frameworks = ["IOKit", "Foundation", "CoreFoundation"]
