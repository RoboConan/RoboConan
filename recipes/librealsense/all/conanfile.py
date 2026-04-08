import os
import textwrap
import urllib

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibrealsenseConan(ConanFile):
    name = "librealsense"
    description = "Intel(R) RealSense(tm) Cross Platform API for accessing Intel RealSense cameras."
    license = "Apache-2.0"
    homepage = "https://github.com/IntelRealSense/librealsense"
    topics = ("usb", "camera")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tools": [True, False],
        "rsusb_backend": [True, False],
        "with_cuda": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "tools": True,
        "rsusb_backend": True, # TODO: change to False when CI gets MSVC ATL support
        "with_cuda": False,
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            del self.options.rsusb_backend

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libusb/[^1.0.26]")
        if Version(self.version) >= "2.50.0":
            self.requires("libudev/[>=255 <system]")
        # Used only in .cpp files
        self.requires("openmp/system")
        if self.options.with_cuda:
            self.cuda.requires("cudart")
            self.cuda.requires("cublas")
            self.cuda.requires("cusparse")

    def validate(self):
        check_min_cppstd(self, 14)
        if self.options.with_cuda:
            self.cuda.validate_settings()

    def build_requirements(self):
        self.tool_requires("cmake/[>=4]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["source"], strip_root=True)
        apply_conandata_patches(self)
        for firmware in sources["firmware"]:
            filename = os.path.basename(urllib.parse.urlparse(firmware["url"]).path)
            download(self, filename=filename, **firmware)
        # Replace https://github.com/IntelRealSense/librealsense/blob/v2.57.2/CMake/cuda_config.cmake
        save(self, "CMake/cuda_config.cmake", textwrap.dedent("""
            cmake_minimum_required(VERSION 3.18)
            enable_language(CUDA)
            find_package(CUDAToolkit REQUIRED)
            link_libraries(CUDA::cusparse CUDA::cublas CUDA::cudart)
            set(CUDA_SEPARABLE_COMPILATION ON)
            list(APPEND CUDA_NVCC_FLAGS "-O3")
        """))

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CHECK_FOR_UPDATES"] = False
        tc.variables["BUILD_WITH_STATIC_CRT"] = is_msvc_static_runtime(self)
        tc.variables["BUILD_EASYLOGGINGPP"] = False
        tc.variables["BUILD_TOOLS"] = self.options.tools
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_GLSL_EXTENSIONS"] = False
        tc.variables["BUILD_GRAPHICAL_EXAMPLES"] = False
        tc.variables["BUILD_INTERNAL_UNIT_TESTS"] = False
        tc.variables["BUILD_NETWORK_DEVICE"] = False
        tc.variables["BUILD_UNIT_TESTS"] = False
        tc.variables["BUILD_WITH_CUDA"] = self.options.with_cuda
        tc.variables["BUILD_WITH_OPENMP"] = True
        tc.variables["BUILD_WITH_TM2"] = True
        tc.variables["BUILD_PYTHON_BINDINGS"] = False
        tc.variables["BUILD_PYTHON_DOCS"] = False
        tc.variables["BUILD_NODEJS_BINDINGS"] = False
        tc.variables["BUILD_CV_EXAMPLES"] = False
        tc.variables["BUILD_DLIB_EXAMPLES"] = False
        tc.variables["BUILD_OPENVINO_EXAMPLES"] = False
        tc.variables["BUILD_OPEN3D_EXAMPLES"] = False
        tc.variables["BUILD_MATLAB_BINDINGS"] = False
        tc.variables["BUILD_PCL_EXAMPLES"] = False
        tc.variables["BUILD_UNITY_BINDINGS"] = False
        tc.variables["BUILD_CSHARP_BINDINGS"] = False
        tc.variables["BUILD_OPENNI2_BINDINGS"] = False
        tc.variables["BUILD_CV_KINFU_EXAMPLE"] = False
        if self.settings.os == "Windows":
            tc.variables["FORCE_RSUSB_BACKEND"] = self.options.rsusb_backend
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.8"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            postfix = "d" if is_msvc(self) and self.settings.build_type == "Debug" else ""
            rm(self, f"libfw{postfix}.*", os.path.join(self.package_folder, "lib"))
            rm(self, f"librealsense-file{postfix}.*", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "realsense2")

        postfix = "d" if is_msvc(self) and self.settings.build_type == "Debug" else ""
        if not self.options.shared:
            self.cpp_info.components["fw"].set_property("cmake_target_name", "realsense2::fw")
            self.cpp_info.components["fw"].libs = [f"fw{postfix}"]
            self.cpp_info.components["realsense-file"].set_property("cmake_target_name", "realsense2::realsense-file")
            self.cpp_info.components["realsense-file"].libs = [f"realsense-file{postfix}"]

        self.cpp_info.components["realsense2"].set_property("cmake_target_name", "realsense2::realsense2")
        self.cpp_info.components["realsense2"].set_property("pkg_config_name", "realsense2")
        self.cpp_info.components["realsense2"].libs = [f"realsense2{postfix}"]
        if not self.options.shared:
            self.cpp_info.components["realsense2"].requires.extend(["realsense-file", "fw"])
        self.cpp_info.components["realsense2"].requires = ["libusb::libusb", "openmp::openmp"]
        if Version(self.version) >= "2.50.0":
            self.cpp_info.components["realsense2"].requires.append("libudev::libudev")
        if self.options.with_cuda:
            self.cpp_info.components["realsense2"].requires.extend([
                "cudart::cudart_",
                "cublas::cublas_",
                "cusparse::cusparse",
            ])
        if self.settings.os == "Linux":
            self.cpp_info.components["realsense2"].system_libs.extend(["m", "pthread"])
        elif self.settings.os == "Windows":
            self.cpp_info.components["realsense2"].system_libs.extend([
                "cfgmgr32", "setupapi",
                "sensorsapi", "portabledeviceguids",
                "winusb",
                "shlwapi", "mf", "mfplat", "mfreadwrite", "mfuuid"
            ])
