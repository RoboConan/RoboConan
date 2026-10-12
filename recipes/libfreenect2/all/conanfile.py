import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class Libfreenect2Conan(ConanFile):
    name = "libfreenect2"
    description = "Open source drivers for the Kinect for Windows v2 device."
    license = "Apache-2.0 OR GPL-2.0"
    homepage = "https://github.com/OpenKinect/libfreenect2"
    topics = ("usb", "camera", "kinect")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_opencl": [True, False],
        "with_opengl": [True, False],
        "with_vaapi": [True, False],
        "with_cuda": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_opencl": True,
        "with_opengl": True,
        "with_vaapi": True,
        "with_cuda": False,
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os not in ["Linux", "FreeBSD"]:
            self.options.rm_safe("with_vaapi")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libusb/[^1.0.26]")
        self.requires("libjpeg-meta/latest")
        if self.options.with_opencl:
            # 2023.02.06 is the latest compatible version
            self.requires("opencl-headers/2023.02.06")
            self.requires("opencl-icd-loader/2023.02.06")
        if self.options.with_opengl:
            self.requires("opengl/system")
            self.requires("glfw/[^3.3.8]")
        if self.options.get_safe("with_vaapi"):
            self.requires("libva/[^2.21]")
        if self.options.with_cuda:
            self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)
            self.cuda.requires("cuda-samples")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.dependencies["libjpeg-meta"].options.provider not in ["libjpeg-turbo", "mozjpeg"]:
            raise ConanException("libjpeg-meta provider must be either libjpeg-turbo or mozjpeg")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # The CMake target for OpenGL works more reliably with libglvnd
        replace_in_file(self, "CMakeLists.txt", "${OPENGL_gl_LIBRARY}", "OpenGL::GL")
        replace_in_file(self, "CMakeLists.txt", "FIND_PACKAGE(JPEG)", "FIND_PACKAGE(TurboJPEG REQUIRED CONFIG)")
        replace_in_file(self, "CMakeLists.txt", " JPEG_FOUND", " TRUE")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "NONE"
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_OPENNI2_DRIVER"] = False
        tc.variables["ENABLE_CXX11"] = True
        tc.variables["ENABLE_OPENCL"] = self.options.with_opencl
        tc.variables["ENABLE_CUDA"] = self.options.with_cuda
        tc.variables["ENABLE_OPENGL"] = self.options.with_opengl
        tc.variables["ENABLE_VAAPI"] = self.options.get_safe("with_vaapi", False)
        tc.variables["ENABLE_TEGRAJPEG"] = False  # TODO: TegraJPEG
        tc.variables["ENABLE_PROFILING"] = False
        if self.options.with_cuda:
            tc.variables["NVCUDASAMPLES_ROOT"] = os.path.join(self.dependencies["cuda-samples"].package_folder, "include")
            # Required for deprecated FindCUDA support
            tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0146"] = "OLD"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        if Version(self.version) > "0.2.1":
            raise ConanException("CMAKE_POLICY_VERSION_MINIMUM hardcoded to 3.5, check if new version supports CMake 4")
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("libusb", "cmake_file_name", "LibUSB")
        deps.set_property("glfw3", "cmake_file_name", "GLFW3")
        deps.set_property("libjpeg-meta", "cmake_file_name", "TurboJPEG")
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
        copy(self, "APACHE20",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False)
        copy(self, "GPL2",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "freenect2")
        self.cpp_info.set_property("cmake_target_name", "freenect2::freenect2")
        self.cpp_info.set_property("pkg_config_name", "freenect2")
        self.cpp_info.libs = collect_libs(self)
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "pthread", "dl"])
        elif is_apple_os(self):
            self.cpp_info.frameworks.extend(["VideoToolbox", "CoreFoundation", "CoreMedia", "CoreVideo"])

        self.cpp_info.requires += [
            "libusb::libusb",
            "libjpeg-meta::jpeg",
            "libjpeg-meta::turbojpeg",
        ]
        if self.options.with_opencl:
            self.cpp_info.requires += [
                "opencl-headers::opencl-headers",
                "opencl-icd-loader::opencl-icd-loader",
            ]
        if self.options.with_opengl:
            self.cpp_info.requires += [
                "opengl::opengl",
                "glfw::glfw",
            ]
        if self.options.get_safe("with_vaapi"):
            self.cpp_info.requires += ["libva::libva"]
        if self.options.with_cuda:
            self.cpp_info.requires += [
                "cudart::cudart_",
                "cuda-samples::cuda-samples",
            ]
