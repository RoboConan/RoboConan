import os
import textwrap
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc, msvc_runtime_flag
from conan.tools.scm import Version

required_conan_version = ">=2.21"  # for cmake_extra_variables


OPENCV_MAIN_MODULES_OPTIONS = (
    "calib",
    "dnn",
    "features",
    "flann",
    "geometry",
    "highgui",
    "imgcodecs",
    "imgproc",
    "objdetect",
    "photo",
    "ptcloud",
    "stereo",
    "stitching",
    "video",
    "videoio",
)

OPENCV_EXTRA_MODULES_OPTIONS = (
    "alphamat",
    "bgsegm",
    "bioinspired",
    "ccalib",
    "cudaarithm",
    "cudabgsegm",
    "cudacodec",
    "cudafeatures2d",
    "cudafilters",
    "cudaimgproc",
    "cudalegacy",
    "cudaobjdetect",
    "cudaoptflow",
    "cudastereo",
    "cudawarping",
    "cvv",
    "datasets",
    "dnn_objdetect",
    "dnn_superres",
    "dpm",
    "face",
    "freetype",
    "fuzzy",
    "gapi",
    "hdf",
    "hfs",
    "img_hash",
    "intensity_transform",
    "line_descriptor",
    "ml",
    "optflow",
    "ovis",
    "phase_unwrapping",
    "plot",
    "quality",
    "rapid",
    "reg",
    "rgbd",
    "saliency",
    "sfm",
    "shape",
    "signal",
    "structured_light",
    "superres",
    "surface_matching",
    "text",
    "tracking",
    "videostab",
    "viz",
    "wechat_qrcode",
    "xfeatures2d",
    "ximgproc",
    "xobjdetect",
    "xphoto",
    "xstereo",
)

class OpenCVConan(ConanFile):
    name = "opencv"
    license = "Apache-2.0"
    homepage = "https://opencv.org"
    description = "OpenCV (Open Source Computer Vision Library)"
    topics = ("computer-vision", "deep-learning", "image-processing")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],

        # Global ABI / implementation choices.
        "parallel": [False, "tbb", "openmp"],
        "with_ipp": [True, False],
        "with_armpl": [True, False],
        "with_cpu_features": [True, False],
        "with_eigen": [True, False],
        "with_lapack": [True, False],
        "with_opencl": [True, False],
        "with_opencl_clblas": [True, False],
        "with_opencl_clfft": [True, False],
        "with_cuda": [True, False],
        "with_cublas": [True, False],
        "with_cufft": [True, False],
        "with_itt": [True, False],
        "cpu_baseline": [None, "ANY"],
        "cpu_dispatch": [None, "ANY"],
        "world": [True, False],
        "nonfree": [True, False],

        # DNN integrations.
        "with_flatbuffers": [True, False],
        "with_protobuf": [True, False],
        "with_vulkan": [True, False],
        "with_openvino": [True, False],
        "with_onnxruntime": [True, False],
        "dnn_cuda": [True, False],

        # HighGUI / platform UI integrations.
        "with_framebuffer": [True, False],
        "with_framebuffer_xvfb": [True, False],
        "with_gtk": [True, False],
        "with_qt": [True, False],
        "with_wayland": [True, False],
        "with_opengl": [True, False],
        "with_win32ui": [True, False],

        # Image codecs. SPNG is an alternative PNG implementation, not an
        # independent second codec, so make the selection a single option.
        "with_avif": [True, False],
        "with_jpeg": [True, False],
        "with_jpegxl": [True, False],
        "with_jpeg2000": [False, "jasper", "openjpeg"],
        "with_png": [False, "libpng", "libspng"],
        "with_tiff": [True, False],
        "with_openexr": [True, False],
        "with_webp": [True, False],
        "with_gdal": [True, False],
        "with_gdcm": [True, False],
        "with_imgcodec_gif": [True, False],
        "with_imgcodec_hdr": [True, False],
        "with_imgcodec_pfm": [True, False],
        "with_imgcodec_pxm": [True, False],
        "with_imgcodec_sunraster": [True, False],
        "with_unifont": [True, False],

        # Video I/O. System backends are options because they change the
        # compiled package even though they do not all add Conan requirements.
        "with_1394": [True, False],
        "with_aravis": [True, False],
        "with_ffmpeg": [True, False],
        "with_ffmpeg_libavdevice": [True, False],
        "with_gphoto2": [True, False],
        "with_gstreamer": [True, False],
        "with_librealsense": [True, False],
        "with_openni2": [True, False],
        "with_obsensor": [True, False],
        "with_va": [True, False],
        "with_va_intel": [True, False],
        "with_v4l": [True, False],
        "with_dshow": [True, False],
        "with_msmf": [True, False],
        "with_msmf_dxva": [True, False],
        "with_directx": [True, False],
        "with_avfoundation": [True, False],
        "with_cap_ios": [True, False],
        "with_android_mediandk": [True, False],
        "with_android_native_camera": [True, False],

        # CUDA modules have independently optional NVIDIA SDK integrations.
        "with_nvcuvid": [True, False],
        "with_nvcuvenc": [True, False],
        "with_nvidia_optical_flow": [True, False],

        # Contrib external integrations.
        "with_tesseract": [True, False],
        "with_clp": [True, False],
        "with_iconv": [True, False],
        "with_ceres": [True, False],
        "with_freetype": [True, False],

        # Force all main module options to True.
        "build_all_base": [True, False],
        # Force all contrib module options to True.
        "build_all_contrib": [True, False],
    }
    options.update({_name: [True, False] for _name in OPENCV_MAIN_MODULES_OPTIONS})
    options.update({_name: [True, False] for _name in OPENCV_EXTRA_MODULES_OPTIONS})

    default_options = {
        "shared": False,
        "fPIC": True,

        # Global ABI / implementation choices.
        "parallel": "openmp",
        "with_ipp": False,
        "with_armpl": False,
        "with_cpu_features": True,
        "with_eigen": True,
        "with_lapack": False,
        "with_opencl": False,
        "with_opencl_clblas": False,
        "with_opencl_clfft": False,
        "with_cuda": False,
        "with_cublas": False,
        "with_cufft": False,
        "with_itt": False,
        "cpu_baseline": None,
        "cpu_dispatch": None,
        "world": False,
        "nonfree": False,

        # DNN integrations.
        "with_flatbuffers": False,
        "with_protobuf": False,
        "with_vulkan": False,
        "with_openvino": False,
        "with_onnxruntime": False,
        "dnn_cuda": False,

        # HighGUI / platform UI integrations.
        "with_framebuffer": False,
        "with_framebuffer_xvfb": False,
        "with_gtk": False,
        "with_qt": True,
        "with_wayland": False,
        "with_opengl": False,
        "with_win32ui": True,

        # Image codecs.
        "with_avif": False,
        "with_jpeg": True,
        "with_jpegxl": False,
        "with_jpeg2000": False,
        "with_png": "libpng",
        "with_tiff": True,
        "with_openexr": False,
        "with_webp": True,
        "with_gdal": False,
        "with_gdcm": False,
        "with_imgcodec_gif": True,
        "with_imgcodec_hdr": True,
        "with_imgcodec_pfm": True,
        "with_imgcodec_pxm": True,
        "with_imgcodec_sunraster": True,
        "with_unifont": True,

        # Video I/O.
        "with_1394": False,
        "with_aravis": False,
        "with_ffmpeg": True,
        "with_ffmpeg_libavdevice": False,
        "with_gphoto2": False,
        "with_gstreamer": False,
        "with_librealsense": False,
        "with_openni2": False,
        "with_obsensor": True,
        "with_va": False,
        "with_va_intel": False,
        "with_v4l": True,
        "with_dshow": True,
        "with_msmf": True,
        "with_msmf_dxva": True,
        "with_directx": True,
        "with_avfoundation": True,
        "with_cap_ios": True,
        "with_android_mediandk": True,
        "with_android_native_camera": True,

        # CUDA modules' optional NVIDIA SDK integrations.
        "with_nvcuvid": False,
        "with_nvcuvenc": False,
        "with_nvidia_optical_flow": False,

        # Contrib external integrations.
        "with_tesseract": True,
        "with_clp": False,
        "with_iconv": True,
        "with_ceres": True,
        "with_freetype": False,

        # OpenCV's VTK integration requires these components.
        "vtk/*:want_all_modules": False,
        "vtk/*:FiltersExtraction": "YES",
        "vtk/*:FiltersSources": "YES",
        "vtk/*:FiltersTexture": "YES",
        "vtk/*:IOExport": "YES",
        "vtk/*:IOGeometry": "YES",
        "vtk/*:IOPLY": "YES",
        "vtk/*:InteractionStyle": "YES",
        "vtk/*:RenderingCore": "YES",
        "vtk/*:RenderingLOD": "YES",
        "vtk/*:RenderingOpenGL2": "YES",
        "vtk/*:with_diy2": True,
        "vtk/*:with_eigen": True,
        "vtk/*:with_expat": True,
        "vtk/*:with_jsoncpp": True,
        "vtk/*:with_libharu": True,

        # Main OpenCV modules.
        "calib": True,
        "dnn": False,
        "features": True,
        "flann": True,
        "geometry": True,
        "highgui": False,
        "imgcodecs": True,
        "imgproc": True,
        "objdetect": True,
        "photo": True,
        "ptcloud": False,
        "stereo": True,
        "stitching": True,
        "video": True,
        "videoio": False,

        "build_all_base": False,
        "build_all_contrib": False,
    }
    default_options.update({_name: False for _name in OPENCV_EXTRA_MODULES_OPTIONS})

    @property
    def _build_depends_on_pkgconfig(self):
        # Keep this in sync with both build_requirements() and generate()'s
        # PkgConfigDeps creation.
        return any(self.options.get_safe(option) for option in (
            "with_clp",
            "with_1394",
            "with_aravis",
            "with_gphoto2",
            "with_gstreamer",
            "with_gtk",
            "with_wayland",
        )) or (
            self.options.get_safe("gapi")
            and self.options.get_safe("with_freetype")
        )

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _is_cl_like(self):
        return self.settings.compiler.get_safe("runtime") is not None

    @property
    def _is_cl_like_static_runtime(self):
        return self._is_cl_like and "MT" in msvc_runtime_flag(self)

    @property
    def _is_mingw(self):
        return self.settings.os == "Windows" and self.settings.compiler == "gcc"

    @property
    def _contrib_folder(self):
        return os.path.join(self.source_folder, "contrib")

    @property
    def _extra_modules_folder(self):
        return os.path.join(self._contrib_folder, "modules")

    @property
    def _is_apple_device_os(self):
        return is_apple_os(self) and self.settings.os != "Macos"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

        if self.settings.os not in ("Linux", "Windows") or self.settings.arch != "x86_64":
            del self.options.with_ipp
        if self.settings.os != "Android":
            del self.options.with_cpu_features

        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_gtk
        if self.settings.os != "Linux":
            del self.options.with_v4l
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_framebuffer
            del self.options.with_framebuffer_xvfb
            del self.options.with_va
            del self.options.with_va_intel
        if self.settings.os != "Linux":
            del self.options.with_wayland
        if self.settings.os in ("WindowsStore", "iOS", "visionOS"):
            del self.options.with_opencl
        if self.settings.os in ("Android", "WindowsStore", "iOS", "visionOS"):
            del self.options.with_opencl_clblas
            del self.options.with_opencl_clfft
        if self.settings.os not in ["Linux", "FreeBSD", "SunOS", "Windows", "Macos"]:
            del self.options.with_opengl

        if self.settings.os not in ["Windows", "WindowsStore"]:
            del self.options.with_dshow
            del self.options.with_msmf
            del self.options.with_msmf_dxva
            del self.options.with_directx
            del self.options.with_win32ui
        elif self.settings.os == "WindowsStore":
            del self.options.with_dshow
            del self.options.with_directx
            del self.options.with_win32ui
        elif self.settings.arch == "armv8_32":
            del self.options.with_dshow

        if not is_apple_os(self):
            del self.options.with_avfoundation
        if self.settings.os != "iOS":
            del self.options.with_cap_ios
        if self.settings.os != "Android":
            del self.options.with_android_mediandk
            del self.options.with_android_native_camera
        else:
            android_api = int(self.settings.get_safe("os.api_level") or 0)
            if android_api < 21:
                del self.options.with_android_mediandk
            if android_api < 24:
                del self.options.with_android_native_camera

        if self.settings.os in ("WindowsStore", "iOS", "visionOS"):
            del self.options.with_ffmpeg
            del self.options.with_ffmpeg_libavdevice

        if self.settings.os in ("Android", "WindowsStore", "iOS", "visionOS"):
            del self.options.with_gstreamer
        if self.settings.os in ["Android", "Windows", "WindowsStore"] or self._is_apple_device_os:
            del self.options.with_1394
            del self.options.with_aravis
            del self.options.with_gphoto2
        if self.settings.os not in ["Linux", "Macos"]:
            del self.options.with_openni2

        if self.settings.os in ("iOS", "visionOS"):
            del self.options.with_jpeg2000
            del self.options.with_tiff
        if self.settings.os == "iOS":
            del self.options.superres

        if not (self.settings.os in ["Linux", "FreeBSD"] and self.settings.arch == "armv8"):
            del self.options.with_armpl

        if self._is_mingw:
            del self.options.with_msmf
            del self.options.with_msmf_dxva

        if self.settings.os == "WindowsStore":
            del self.options.with_eigen
            del self.options.with_lapack
            del self.options.with_qt
            del self.options.with_webp
            del self.options.with_openexr
            del self.options.with_gdal
            del self.options.dnn
            del self.options.superres
            del self.options.with_cuda
        elif self.settings.os in ("Android", "iOS", "visionOS"):
            del self.options.with_lapack
            del self.options.with_qt
            del self.options.with_gdal
            del self.options.viz
            if self.settings.os in ("iOS", "visionOS"):
                del self.options.with_cuda

        obsensor_supported = (
            (self.settings.os == "Windows" and self.settings.arch != "armv8_32" and not self._is_mingw)
            or self.settings.os in ["Linux", "FreeBSD"]
        )
        if not obsensor_supported:
            del self.options.with_obsensor

        if is_msvc(self) and self.settings.arch == "armv8":
            # https://github.com/opencv/opencv/issues/25052
            # https://github.com/opencv/opencv/pull/24698#issuecomment-1858023908
            self.options.cpu_baseline = "NEON"
            self.options.cpu_dispatch = ""

    def _solve_internal_dependency_graph(self, opencv_modules):
        disabled_options = _mandatory_disabled_options(self.options, opencv_modules)
        enabled_options = {}
        for option, required_by in disabled_options.items():
            value = self.options.get_safe(option)
            if value is not None:
                value.value = True
                enabled_options[option] = required_by

        if enabled_options:
            message = "Enabling OpenCV options required by other enabled modules:\n"
            for option, required_by in sorted(enabled_options.items()):
                message += f"  - {option}: required by {', '.join(sorted(required_by))}\n"
            self.output.warning(message)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

        if self.options.build_all_base:
            for module in OPENCV_MAIN_MODULES_OPTIONS:
                value = self.options.get_safe(module)
                if value is not None:
                    value.value = True
        if self.options.build_all_contrib:
            for module in OPENCV_EXTRA_MODULES_OPTIONS:
                value = self.options.get_safe(module)
                if value is not None:
                    value.value = True

        self._solve_internal_dependency_graph(_opencv_modules(self.options, self.settings))

        if not (self.options.get_safe("gapi") or self.options.get_safe("dnn")):
            self.options.rm_safe("with_openvino")

        if not self.options.get_safe("dnn"):
            self.options.rm_safe("dnn_cuda")
            self.options.rm_safe("with_flatbuffers")
            self.options.rm_safe("with_protobuf")
            self.options.rm_safe("with_vulkan")
        if not (self.options.get_safe("dnn") or self.options.get_safe("gapi")):
            self.options.rm_safe("with_onnxruntime")

        if not self.options.highgui:
            self.options.rm_safe("with_framebuffer")
            self.options.rm_safe("with_framebuffer_xvfb")
            self.options.rm_safe("with_gtk")
            self.options.rm_safe("with_wayland")
            self.options.rm_safe("with_win32ui")
        if not (self.options.highgui or self.options.get_safe("cvv")):
            self.options.rm_safe("with_qt")
        if not self.options.imgcodecs:
            self.options.rm_safe("with_avif")
            self.options.rm_safe("with_jpeg")
            self.options.rm_safe("with_jpegxl")
            self.options.rm_safe("with_jpeg2000")
            self.options.rm_safe("with_png")
            self.options.rm_safe("with_openexr")
            self.options.rm_safe("with_tiff")
            self.options.rm_safe("with_webp")
            self.options.rm_safe("with_gdal")
            self.options.rm_safe("with_gdcm")
            self.options.rm_safe("with_imgcodec_gif")
            self.options.rm_safe("with_imgcodec_hdr")
            self.options.rm_safe("with_imgcodec_pfm")
            self.options.rm_safe("with_imgcodec_pxm")
            self.options.rm_safe("with_imgcodec_sunraster")
        if not self.options.imgproc:
            self.options.rm_safe("with_unifont")

        if not self.options.videoio:
            self.options.rm_safe("with_1394")
            self.options.rm_safe("with_aravis")
            self.options.rm_safe("with_ffmpeg")
            self.options.rm_safe("with_ffmpeg_libavdevice")
            self.options.rm_safe("with_gphoto2")
            self.options.rm_safe("with_librealsense")
            self.options.rm_safe("with_openni2")
            self.options.rm_safe("with_obsensor")
            self.options.rm_safe("with_v4l")
            self.options.rm_safe("with_dshow")
            self.options.rm_safe("with_msmf_dxva")
            self.options.rm_safe("with_avfoundation")
            self.options.rm_safe("with_cap_ios")
            self.options.rm_safe("with_android_mediandk")
            self.options.rm_safe("with_android_native_camera")
        if not (self.options.videoio or self.options.get_safe("gapi")):
            self.options.rm_safe("with_gstreamer")
            self.options.rm_safe("with_msmf")

        if not self.options.get_safe("with_ffmpeg"):
            self.options.rm_safe("with_ffmpeg_libavdevice")
        if not self.options.get_safe("with_framebuffer"):
            self.options.rm_safe("with_framebuffer_xvfb")
        if not self.options.get_safe("with_va"):
            self.options.rm_safe("with_va_intel")
        if not self.options.get_safe("with_opencl"):
            self.options.rm_safe("with_va_intel")
        if not self.options.get_safe("with_msmf"):
            self.options.rm_safe("with_msmf_dxva")

        if not self.options.get_safe("with_opencl", False):
            self.options.rm_safe("with_opencl_clblas")
            self.options.rm_safe("with_opencl_clfft")

        if not self.options.get_safe("with_cuda"):
            del self.settings.cuda
            self.options.rm_safe("with_cublas")
            self.options.rm_safe("with_cufft")
            self.options.rm_safe("dnn_cuda")
            self.options.rm_safe("with_nvcuvid")
            self.options.rm_safe("with_nvcuvenc")
            self.options.rm_safe("with_nvidia_optical_flow")
        if not self.options.get_safe("cudacodec"):
            self.options.rm_safe("with_nvcuvid")
            self.options.rm_safe("with_nvcuvenc")
        if not self.options.get_safe("cudaoptflow"):
            self.options.rm_safe("with_nvidia_optical_flow")

        if not self.options.get_safe("text"):
            self.options.rm_safe("with_tesseract")
        if not self.options.get_safe("videostab"):
            self.options.rm_safe("with_clp")
        if not self.options.get_safe("wechat_qrcode"):
            self.options.rm_safe("with_iconv")
        if not self.options.get_safe("sfm"):
            self.options.rm_safe("with_ceres")

        if not (self.options.get_safe("gapi") or self.options.get_safe("freetype")):
            self.options.rm_safe("with_freetype")

    def package_id(self):
        del self.info.options.build_all_base
        del self.info.options.build_all_contrib

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # core and global dependencies
        self.requires("zlib-ng/[^2.0]")
        if self.options.get_safe("with_eigen"):
            self.requires("eigen/[>=3.3 <6]")
        if self.options.get_safe("with_lapack"):
            self.requires("lapack/latest")
        if self.options.get_safe("with_armpl"):
            self.requires("armpl/[^25.07.0]")
        if self.options.get_safe("with_cpu_features"):
            self.requires("cpu_features/[>=0.9 <1]")
        if self.options.get_safe("with_clp"):
            self.requires("coin-clp/[^1.17.6]")
        if self.options.get_safe("with_ipp"):
            self.requires("intel-ipp/[^2026.0.1]")

        if self.options.get_safe("with_cuda"):
            # Used by installed opencv2/cudev headers.
            # https://github.com/opencv/opencv_contrib/blob/5.0.0/modules/cudev/include/opencv2/cudev/common.hpp
            self.cuda.requires("cudart", transitive_headers=True)
            # Used by the installed opencv2/core/cuda/filters.hpp header.
            # https://github.com/opencv/opencv/blob/5.0.0/modules/core/include/opencv2/core/cuda/filters.hpp#L50
            self.cuda.requires("npp", transitive_headers=True)
            if self.options.with_cublas:
                self.cuda.requires("cublas")
            if self.options.with_cufft:
                self.cuda.requires("cufft")
            if self.options.get_safe("dnn_cuda"):
                self.requires("cudnn/[>=8 <10]")
            if self.options.get_safe("with_nvcuvid") or self.options.get_safe("with_nvcuvenc"):
                self.cuda.requires("nvidia-video-codec-sdk")
            if self.options.get_safe("with_nvidia_optical_flow"):
                # Included only by the module implementation, not its installed headers.
                # https://github.com/opencv/opencv_contrib/blob/5.0.0/modules/cudaoptflow/src/nvidiaOpticalFlow.cpp#L51-L52
                self.cuda.requires("nvidia-optical-flow-sdk", visible=False)

        if self.options.parallel == "openmp":
            self.requires("openmp/system")
        elif self.options.parallel == "tbb":
            self.requires("onetbb/[>=2021]")
        if self.options.get_safe("with_opencl") and not is_apple_os(self):
            self.requires("opencl-icd-loader/[*]")
        if self.options.get_safe("with_opencl_clblas"):
            # Loaded at runtime rather than linked into OpenCV.
            # https://github.com/opencv/opencv/blob/5.0.0/modules/core/src/opencl/runtime/opencl_clblas.cpp#L79
            self.requires("clblas/[^2.13.0]", libs=False, run=True)
        if self.options.get_safe("with_opencl_clfft"):
            self.requires("clfft/[^2.15.0]")
        if self.options.with_itt:
            self.requires("ittapi/[^3.25.5]")

        # DNN dependencies
        if self.options.get_safe("with_protobuf"):
            # Generated protobuf message types occur in OpenCV's DNN symbols.
            # https://github.com/opencv/opencv/blob/5.0.0/modules/dnn/CMakeLists.txt#L392-L438
            self.requires("protobuf/[>=3.21.12 <8]", transitive_libs=True)
        if self.options.get_safe("with_flatbuffers"):
            self.requires("flatbuffers/[>=25.9.23 <25.9.24]")
        if self.options.get_safe("with_vulkan"):
            # Included only by DNN's private implementation headers.
            # https://github.com/opencv/opencv/blob/5.0.0/modules/dnn/src/vkcom/include/context.hpp#L30-L32
            self.requires("vulkan-headers/[^1.3.239.0]", visible=False)
        if self.options.get_safe("with_openvino"):
            self.requires("openvino/[>=2024.5.0 <2026]")
        if self.options.get_safe("with_onnxruntime"):
            self.requires("onnxruntime/[>=1.22.2 <2]")

        # G-API dependencies
        if self.options.get_safe("gapi"):
            self.requires("ade/[^0.1.2d]")
        if self.options.get_safe("with_freetype"):
            self.requires("freetype/[^2.13.2]")

        # HighGUI dependencies
        if self.options.get_safe("with_framebuffer_xvfb"):
            # Included only by the framebuffer implementation.
            # https://github.com/opencv/opencv/blob/5.0.0/modules/highgui/src/window_framebuffer.cpp#L31-L32
            self.requires("xorg-proto/[>=2024.1]", visible=False)
        if self.options.get_safe("with_gtk"):
            self.requires("gtk/[~3.24]")
        if self.options.get_safe("with_qt"):
            self.requires("qt/[>=5.15 <7]")
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22.0]")
            self.requires("xkbcommon/[^1.6.0]")
        if self.options.get_safe("with_opengl"):
            self.requires("opengl/system")

        # imgcodecs dependencies
        if self.options.get_safe("with_avif"):
            self.requires("libavif/[^1.0.4]")
        if self.options.get_safe("with_jpeg"):
            self.requires("libjpeg-meta/latest")
        if self.options.get_safe("with_jpegxl"):
            self.requires("libjxl/[>=0.11.1 <1]")
        if self.options.get_safe("with_jpeg2000") == "openjpeg":
            self.requires("openjpeg/[^2.5.2]")
        elif self.options.get_safe("with_jpeg2000") == "jasper":
            self.requires("jasper/[^4.2]")
        if self.options.get_safe("with_png") == "libpng":
            self.requires("libpng/[~1.6]")
        elif self.options.get_safe("with_png") == "libspng":
            self.requires("libspng/[^0.7.4]")
        if self.options.get_safe("with_openexr"):
            self.requires("openexr/[^3.3.3]")
        if self.options.get_safe("with_tiff"):
            self.requires("libtiff/[^4.5]")
        if self.options.get_safe("with_webp"):
            self.requires("libwebp/[^1.3.2]")
        if self.options.get_safe("with_gdal"):
            self.requires("gdal/[^3.10.0]")
        if self.options.get_safe("with_gdcm"):
            self.requires("gdcm/[^3.0.23]")

        # videoio dependencies
        if self.options.get_safe("with_ffmpeg"):
            self.requires("ffmpeg/[>=4.4.6 <9]")
        if self.options.get_safe("with_gstreamer"):
            self.requires("gst-plugins-base/[^1.16]")
            self.requires("gstreamer/[^1.16]")
        if self.options.get_safe("with_1394"):
            self.requires("libdc1394/[^2.2.6]")
        if self.options.get_safe("with_aravis"):
            self.requires("aravis/[>=0.8.30 <1]")
        if self.options.get_safe("with_gphoto2"):
            self.requires("libgphoto2/[^2.5.31]")
        if self.options.get_safe("with_librealsense"):
            self.requires("librealsense/[^2.53.1]")
        if self.options.get_safe("with_openni2"):
            self.requires("openni2/[^2.2.0]")
        if self.options.get_safe("with_va"):
            self.requires("libva/[^2.20.0]")

        # contrib module dependencies
        if self.options.get_safe("freetype"):
            self.requires("harfbuzz/[>=6 <12]")
        if self.options.get_safe("hdf"):
            self.requires("hdf5/[^1.8]")
        if self.options.get_safe("ovis"):
            self.requires("ogre/[^14.3]")
        if self.options.get_safe("sfm"):
            self.requires("gflags/[^2.2.2]")
            self.requires("glog/[>=0.6 <1]")
            if self.options.get_safe("with_ceres"):
                self.requires("ceres-solver/[^2.2.0, include_prerelease]")
        if self.options.get_safe("text") and self.options.get_safe("with_tesseract"):
            self.requires("tesseract/[^5.3.3]")
        if self.options.get_safe("viz"):
            self.requires("vtk/[^9.3.1]")
        if self.options.get_safe("wechat_qrcode") and self.options.get_safe("with_iconv"):
            self.requires("libiconv/[^1.18]")

    def _check_mandatory_options(self, opencv_modules):
        disabled_options = _mandatory_disabled_options(self.options, opencv_modules)
        if disabled_options:
            message = "OpenCV options required by enabled modules are unavailable:\n"
            for option, required_by in sorted(disabled_options.items()):
                message += f"  - {option}: required by {', '.join(sorted(required_by))}\n"
            raise ConanInvalidConfiguration(message)

    def validate(self):
        self._check_mandatory_options(_opencv_modules(self.options, self.settings))
        check_min_cppstd(self, 17)

        if not self.dependencies["zlib-ng"].options.zlib_compat:
            raise ConanInvalidConfiguration("OpenCV requires zlib-ng:zlib_compat=True")

        if self.options.shared and self._is_cl_like and self._is_cl_like_static_runtime:
            raise ConanInvalidConfiguration("MSVC or clang-cl with static runtime are not supported for shared library.")

        if self.options.get_safe("dnn_cuda") and (
            not self.options.get_safe("with_cuda") or not self.options.get_safe("with_cublas")
        ):
            raise ConanInvalidConfiguration("dnn_cuda requires with_cuda=True and with_cublas=True")

        if (
            self.options.get_safe("with_ffmpeg_libavdevice")
            and not self.dependencies["ffmpeg"].options.avdevice
        ):
            raise ConanInvalidConfiguration(
                "with_ffmpeg_libavdevice requires ffmpeg:avdevice=True"
            )

        if (
            self.options.get_safe("cvv")
            and Version(self.dependencies["qt"].ref.version) >= "6"
            and str(self.dependencies["qt"].options.qt5compat) != "True"
        ):
            raise ConanInvalidConfiguration("cvv with Qt6 requires -o 'qt/*:qt5compat=True'")

        if self.options.get_safe("with_nvidia_optical_flow") and Version(self.settings.cuda.version) < "10":
            raise ConanInvalidConfiguration("with_nvidia_optical_flow requires CUDA 10 or newer")

        for option, dependency in (
            ("with_opencl_clblas", "clblas"),
            ("with_opencl_clfft", "clfft"),
        ):
            if self.options.get_safe(option) and not self.dependencies[dependency].options.shared:
                raise ConanInvalidConfiguration(
                    f"{option} requires {dependency}:shared=True because OpenCV loads it dynamically"
                )

        if self.options.get_safe("with_cuda"):
            self.cuda.validate_settings()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.27 <5]")
        if self.options.get_safe("with_protobuf"):
            self.tool_requires("protobuf/<host_version>")
        if self.options.get_safe("with_wayland"):
            self.tool_requires("wayland/<host_version>")
        if self._build_depends_on_pkgconfig and not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.get_safe("with_qt"):
            self.tool_requires("qt/<host_version>")
        if self.options.get_safe("with_cuda"):
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version][0], strip_root=True)
        get(self, **self.conan_data["sources"][self.version][1], destination="contrib", strip_root=True)

        # OpenCV 5.0.0 omitted this source while retaining the generated files
        # from 4.14.0, preventing regeneration with current protobuf releases.
        caffe_proto = self.conan_data["opencv_caffe_proto"]
        download(self, **caffe_proto,
                 filename=f'modules/dnn/src/caffe/{caffe_proto["url"].rsplit("/", 1)[-1]}')

        for data in self.conan_data["xfeatures2d_data"]:
            path = f'contrib/modules/xfeatures2d/src/{data["url"].rsplit("/", 1)[-1]}'
            download(self, data["url"], path, sha256=data["sha256"])

        unifont = self.conan_data["unifont"]
        path = f'.conan/unifont/{unifont["url"].rsplit("/", 1)[-1]}'
        download(self, unifont["url"], path, sha256=unifont["sha256"])

        apply_conandata_patches(self)

        # Do not restrict multi-config generators to Release and Debug.
        replace_in_file(
            self,
            "CMakeLists.txt",
            "ocv_update(CMAKE_CONFIGURATION_TYPES",
            "# ocv_update(CMAKE_CONFIGURATION_TYPES",
        )

        # Remove bundled copies of dependencies supplied by Conan.
        for directory in (
            "include",
            "cpufeatures",
            "flatbuffers",
            "libjasper",
            "libjpeg-turbo",
            "libpng",
            "libspng",
            "libtiff",
            "libwebp",
            "openjpeg",
            "protobuf",
            "tbb",
            "zlib",
            "zlib-ng",
        ):
            rmdir(self, f"3rdparty/{directory}")

        # The bundled OpenCL headers and their license were removed above.
        replace_in_file(self, "cmake/OpenCVDetectOpenCL.cmake", "ocv_install_3rdparty_licenses", "# ocv_install_3rdparty_licenses")

        # Conan installs the project license into licenses/ itself.
        replace_in_file(self, "CMakeLists.txt", "ANDROID OR NOT UNIX", "FALSE")

        # Prefer dependency targets or the variables emitted by CMakeDeps.
        replace_in_file(self, "modules/imgcodecs/CMakeLists.txt",
            "${GDAL_LIBRARY}",
            "GDAL::GDAL")
        replace_in_file(self, "modules/videoio/cmake/detect_realsense.cmake",
            'ocv_add_external_target(librealsense "" "${realsense2_LIBRARY}" "HAVE_LIBREALSENSE")',
            'ocv_add_external_target(librealsense "${realsense2_INCLUDE_DIRS}" "${realsense2_LIBRARIES}" "HAVE_LIBREALSENSE")')

        # OpenCV's WebP finder does not consume the generated config package.
        save(self, "cmake/OpenCVFindWebP.cmake", textwrap.dedent("""\
            find_package(WebP REQUIRED CONFIG)
            set(WEBP_FOUND "${WebP_FOUND}")
        """))

        # OpenCV's OpenNI2 finder only searches SDK environment variables and
        # fixed system locations, neither of which describes a Conan dependency.
        save(self, "modules/videoio/cmake/detect_openni2.cmake", textwrap.dedent("""\
            find_package(OPENNI2 ${OPENNI2_REQUIRED} CONFIG)
            set(HAVE_OPENNI2 "${OPENNI2_FOUND}")
            ocv_add_external_target(openni2 "${OPENNI2_INCLUDE_DIRS}" "${OPENNI2_LIBRARIES}" "HAVE_OPENNI2")
        """))

        # OpenCV's ARMPL finder only understands a vendor installation tree.
        save(self, "cmake/OpenCVFindARMPL.cmake", textwrap.dedent("""\
            find_package(ARMPL REQUIRED CONFIG)
            set(ARMPL_LIBRARIES armpl)
            set(ARMPL_LIBRARY armpl)
            set(ARMPL_LIB_NAME armpl)
            set(ARMPL_VERSION_STR "${ARMPL_VERSION_STRING}")
            set(HAVE_ARMPL TRUE)
        """))

        # OpenCV vendors the exact FlatBuffers headers used to generate its
        # TFLite schema, but has no external-package discovery path.
        save(self, "cmake/OpenCVDetectFlatbuffers.cmake", textwrap.dedent("""\
            if(WITH_FLATBUFFERS)
              find_package(flatbuffers 25.9.23 EXACT REQUIRED CONFIG)
              set(HAVE_FLATBUFFERS 1)
              ocv_add_external_target(flatbuffers "" flatbuffers::flatbuffers "HAVE_FLATBUFFERS=1")
              set(CUSTOM_STATUS_flatbuffers "    Flatbuffers:" "${flatbuffers_VERSION}")
            endif()

            if(WITH_FLATBUFFERS OR HAVE_FLATBUFFERS)
              list(APPEND CUSTOM_STATUS flatbuffers)
            endif()
        """))

        # Upstream only handles the bundled ITT implementation.
        save(self, "cmake/OpenCVDetectTrace.cmake", textwrap.dedent("""\
            if(WITH_ITT)
                find_package(ITT REQUIRED CONFIG)
                set(HAVE_ITT TRUE)
            endif()
            set(OPENCV_TRACE 1)
        """))

        # Use libjxl through its generated CMake package instead of the manual
        # library search in OpenCVFindJPEGXL.cmake.
        save(self, "cmake/OpenCVFindJPEGXL.cmake", "find_package(JPEGXL REQUIRED CONFIG)\n")

        # A package must not retain absolute build-machine install RPATHs.
        replace_in_file(self, "cmake/OpenCVInstallLayout.cmake",
            'ocv_update(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/${OPENCV_LIB_INSTALL_PATH}")',
            "")
        replace_in_file(self, "cmake/OpenCVInstallLayout.cmake",
            "set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)",
            "")
        # The GTK HighGUI plugin is part of the configured package and must use
        # the C++ standard selected by Conan.
        replace_in_file(self, "modules/highgui/cmake/plugin.cmake", "CXX_STANDARD 11", "")

        # Descriptor tables are fetched by source() with Conan's SHA-256
        # verification, so xfeatures2d must not use its configure-time downloader.
        replace_in_file(self, "contrib/modules/xfeatures2d/CMakeLists.txt",
            "if(NOT OPENCV_SKIP_FEATURES2D_DOWNLOADING)",
            textwrap.dedent("""\
                ocv_append_source_file_compile_definitions(${CMAKE_CURRENT_SOURCE_DIR}/src/boostdesc.cpp "OPENCV_XFEATURES2D_HAS_BOOST_DATA=1")
                ocv_append_source_file_compile_definitions(${CMAKE_CURRENT_SOURCE_DIR}/src/vgg.cpp "OPENCV_XFEATURES2D_HAS_VGG_DATA=1")
                if(FALSE)
            """).rstrip())

        # conan-cuda owns the architecture selection.
        for path in (
            "cmake/OpenCVDetectCUDA.cmake",
            "cmake/OpenCVDetectCUDALanguage.cmake",
        ):
            replace_in_file(self, path, "ocv_set_cuda_arch_bin_and_ptx(", "# ocv_set_cuda_arch_bin_and_ptx(")

    def generate(self):
        with_png = self.options.get_safe("with_png", False)
        with_libpng = with_png == "libpng"
        with_spng = with_png == "libspng"
        with_onnxruntime = self.options.get_safe("with_onnxruntime", False)
        with_opencl_clfft = self.options.get_safe("with_opencl_clfft", False)
        with_opencl_clblas = self.options.get_safe("with_opencl_clblas", False)
        with_nvcuvid = self.options.get_safe("with_nvcuvid", False)
        with_nvcuvenc = self.options.get_safe("with_nvcuvenc", False)
        android_api = int(self.settings.get_safe("os.api_level") or 0)

        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0099"] = "NEW"
        tc.variables["OPENCV_CONFIG_INSTALL_PATH"] = "cmake"
        tc.variables["OPENCV_BIN_INSTALL_PATH"] = "bin"
        tc.variables["OPENCV_LIB_INSTALL_PATH"] = "lib"
        tc.variables["OPENCV_LIB_ARCHIVE_INSTALL_PATH"] = "lib"
        tc.variables["OPENCV_3P_LIB_INSTALL_PATH"] = "lib"
        tc.variables["OPENCV_LICENSES_INSTALL_PATH"] = "licenses"
        tc.variables["OPENCV_OTHER_INSTALL_PATH"] = "share/opencv5"
        if self.settings.os == "Windows":
            tc.variables["OPENCV_INCLUDE_INSTALL_PATH"] = "include"
        elif self.settings.os == "Neutrino":
            tc.variables["OPENCV_INCLUDE_INSTALL_PATH"] = "usr/include/OpenCV/opencv5"
        else:
            tc.variables["OPENCV_INCLUDE_INSTALL_PATH"] = "include/opencv5"
        tc.variables["INSTALL_CREATE_DISTRIB"] = False
        tc.variables["INSTALL_C_EXAMPLES"] = False
        tc.variables["INSTALL_PYTHON_EXAMPLES"] = False
        tc.variables["INSTALL_ANDROID_EXAMPLES"] = False
        tc.variables["INSTALL_TESTS"] = False
        tc.variables["INSTALL_TO_MANGLED_PATHS"] = False

        # Never build or download private copies of dependencies.
        tc.variables["OPENCV_FORCE_3RDPARTY_BUILD"] = False
        tc.variables["BUILD_CLAPACK"] = False
        tc.variables["BUILD_IPP_IW"] = False
        tc.variables["BUILD_ITT"] = False
        tc.variables["BUILD_JASPER"] = False
        tc.variables["BUILD_JPEG"] = False
        tc.variables["BUILD_OPENJPEG"] = False
        tc.variables["BUILD_PNG"] = False
        tc.variables["BUILD_PROTOBUF"] = False
        tc.variables["BUILD_SPNG"] = False
        tc.variables["BUILD_TBB"] = False
        tc.variables["BUILD_TIFF"] = False
        tc.variables["BUILD_TIMVX"] = False
        tc.variables["BUILD_WEBP"] = False
        tc.variables["BUILD_ZLIB"] = False
        tc.variables["DOWNLOAD_ONNXRUNTIME"] = False
        tc.variables["DOWNLOAD_ONNXRUNTIME_GPU"] = False

        # Package contents: libraries only, plus the modules explicitly selected
        # by the Conan options below.
        tc.variables["BUILD_CUDA_STUBS"] = False
        tc.variables["BUILD_DOCS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_FAT_JAVA_LIB"] = False
        tc.variables["BUILD_JAVA"] = False
        tc.variables["BUILD_KOTLIN_EXTENSIONS"] = False
        tc.variables["BUILD_OBJC"] = False
        tc.variables["BUILD_PACKAGE"] = False
        tc.variables["BUILD_PERF_TESTS"] = False
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_USE_SYMLINKS"] = False
        tc.variables["BUILD_opencv_apps"] = False
        tc.variables["BUILD_opencv_java"] = False
        tc.variables["BUILD_opencv_java_bindings_generator"] = False
        tc.variables["BUILD_opencv_js"] = False
        tc.variables["BUILD_opencv_julia"] = False
        tc.variables["BUILD_opencv_matlab"] = False
        tc.variables["BUILD_opencv_python3"] = False
        tc.variables["BUILD_opencv_python_bindings_generator"] = False
        tc.variables["BUILD_opencv_python_tests"] = False
        tc.variables["BUILD_opencv_ts"] = False
        tc.variables["OPENCV_PYTHON_SKIP_DETECTION"] = True
        tc.variables["OPENCV_GENERATE_SETUPVARS"] = False
        tc.variables["OPENCV_GENERATE_PKGCONFIG"] = False

        # Architecture-specific acceleration. Disable integrations for which the
        # recipe has no controlled dependency; retain the in-tree target HALs.
        tc.variables["WITH_KLEIDICV"] = False
        # TODO: Enable these after RoboConan has standalone CANN and FastCV packages.
        tc.variables["WITH_CANN"] = False
        tc.variables["WITH_FASTCV"] = False
        tc.variables["WITH_CPUFEATURES"] = self.options.get_safe("with_cpu_features", False)
        tc.variables["WITH_IPP"] = self.options.get_safe("with_ipp", False)
        if self.options.get_safe("with_ipp"):
            ipp_root = self.dependencies["intel-ipp"].package_folder.replace("\\", "/")
            tc.variables["IPPROOT"] = ipp_root
            tc.variables["IPPIWROOT"] = ipp_root
            tc.variables["BUILD_WITH_DYNAMIC_IPP"] = self.dependencies["intel-ipp"].options.shared
        tc.variables["WITH_ARMPL"] = self.options.get_safe("with_armpl", False)
        tc.variables["WITH_EIGEN"] = self.options.get_safe("with_eigen", False)
        tc.variables["WITH_LAPACK"] = self.options.get_safe("with_lapack", False)
        tc.variables["WITH_ITT"] = self.options.with_itt

        # Parallel backends. pthreads is a platform facility rather than an
        # independently selectable package option.
        tc.variables["WITH_TBB"] = self.options.parallel == "tbb"
        tc.variables["WITH_OPENMP"] = self.options.parallel == "openmp"
        tc.variables["WITH_HPX"] = False
        tc.variables["WITH_PTHREADS_PF"] = self.settings.os not in ("Windows", "WindowsStore") or self._is_mingw

        # Compute APIs and DNN accelerators.
        tc.variables["WITH_OPENCL"] = self.options.get_safe("with_opencl", False)
        tc.variables["WITH_OPENCLAMDFFT"] = with_opencl_clfft
        tc.variables["WITH_OPENCLAMDBLAS"] = with_opencl_clblas
        tc.variables["WITH_VULKAN"] = self.options.get_safe("with_vulkan", False)
        tc.variables["WITH_OPENVINO"] = self.options.get_safe("with_openvino", False)
        tc.variables["WITH_ONNXRUNTIME"] = with_onnxruntime
        tc.variables["WITH_FLATBUFFERS"] = self.options.get_safe("with_flatbuffers", False)
        tc.variables["WITH_PROTOBUF"] = self.options.get_safe("with_protobuf", False)
        tc.variables["WITH_WEBNN"] = False
        tc.variables["WITH_DIRECTML"] = False
        tc.variables["WITH_TIMVX"] = False

        if self.options.get_safe("with_vulkan"):
            tc.variables["VULKAN_INCLUDE_DIRS"] = self.dependencies["vulkan-headers"].cpp_info.includedir.replace("\\", "/")
        if self.options.get_safe("with_protobuf"):
            tc.variables["PROTOBUF_UPDATE_FILES"] = True
        if with_onnxruntime:
            tc.variables["ONNXRUNTIME_PREFER_STATIC"] = not self.dependencies["onnxruntime"].options.shared

        # OpenCL's clFFT/clBLAS detection only needs each package root. OpenCV
        # loads their entry points dynamically at runtime, except for
        # clfftInitSetupData(), which remains a direct link dependency.
        if with_opencl_clfft:
            tc.variables["CLAMDFFT_INCLUDE_DIR"] = self.dependencies["clfft"].cpp_info.includedir.replace("\\", "/")
        if with_opencl_clblas:
            tc.variables["CLAMDBLAS_INCLUDE_DIR"] = self.dependencies["clblas"].cpp_info.includedir.replace("\\", "/")

        if self.options.get_safe("with_opencl") and not is_apple_os(self):
            tc.variables["OPENCL_INCLUDE_DIR"] = self.dependencies["opencl-headers"].cpp_info.includedir.replace("\\", "/")
            tc.variables["OPENCL_LIBRARY"] = "OpenCL::OpenCL"

        # CUDA and optional SDK integrations.
        tc.variables["WITH_CUDA"] = self.options.get_safe("with_cuda", False)
        tc.variables["WITH_CUBLAS"] = self.options.get_safe("with_cublas", False)
        tc.variables["WITH_CUFFT"] = self.options.get_safe("with_cufft", False)
        tc.variables["WITH_CUDNN"] = self.options.get_safe("dnn_cuda", False)
        tc.variables["WITH_NVCUVID"] = with_nvcuvid
        tc.variables["WITH_NVCUVENC"] = with_nvcuvenc
        tc.variables["ENABLE_CUDA_FIRST_CLASS_LANGUAGE"] = self.options.get_safe("with_cuda", False)
        tc.variables["OPENCV_DNN_CUDA"] = self.options.get_safe("dnn_cuda", False)

        if with_nvcuvid or with_nvcuvenc:
            nvcodec = self.dependencies["nvidia-video-codec-sdk"]
            tc.variables["NVIDIA_VIDEO_CODEC_SDK_ROOT"] = nvcodec.package_folder.replace("\\", "/")
            if with_nvcuvid:
                tc.variables["CUDA_nvcuvid_LIBRARY"] = "nvidia-video-codec-sdk::nvcuvid"
            if with_nvcuvenc:
                variable = "CUDA_nvencodeapi_LIBRARY" if self.settings.os == "Windows" else "CUDA_nvidia-encode_LIBRARY"
                tc.variables[variable] = "nvidia-video-codec-sdk::nvidia-encode"
        if self.options.get_safe("with_nvidia_optical_flow"):
            tc.variables["NVIDIA_OPTICAL_FLOW_INCLUDE_DIR"] = self.dependencies[
                "nvidia-optical-flow-sdk"
            ].cpp_info.includedir.replace("\\", "/")

        # Image codecs. OpenCV 5 can use either libpng or libspng, never both.
        tc.variables["WITH_AVIF"] = self.options.get_safe("with_avif", False)
        tc.variables["WITH_JPEG"] = bool(self.options.get_safe("with_jpeg", False))
        tc.variables["WITH_JPEGXL"] = self.options.get_safe("with_jpegxl", False)
        tc.variables["WITH_JASPER"] = self.options.get_safe("with_jpeg2000") == "jasper"
        tc.variables["WITH_OPENJPEG"] = self.options.get_safe("with_jpeg2000") == "openjpeg"
        tc.variables["WITH_PNG"] = with_libpng
        tc.variables["WITH_SPNG"] = with_spng
        tc.variables["WITH_TIFF"] = self.options.get_safe("with_tiff", False)
        tc.variables["WITH_OPENEXR"] = self.options.get_safe("with_openexr", False)
        tc.variables["WITH_WEBP"] = self.options.get_safe("with_webp", False)
        tc.variables["WITH_GDAL"] = self.options.get_safe("with_gdal", False)
        tc.variables["WITH_GDCM"] = self.options.get_safe("with_gdcm", False)
        tc.variables["WITH_IMGCODEC_GIF"] = self.options.get_safe("with_imgcodec_gif", False)
        tc.variables["WITH_IMGCODEC_HDR"] = self.options.get_safe("with_imgcodec_hdr", False)
        tc.variables["WITH_IMGCODEC_PFM"] = self.options.get_safe("with_imgcodec_pfm", False)
        tc.variables["WITH_IMGCODEC_PXM"] = self.options.get_safe("with_imgcodec_pxm", False)
        tc.variables["WITH_IMGCODEC_SUNRASTER"] = self.options.get_safe("with_imgcodec_sunraster", False)
        tc.variables["WITH_ZLIB_NG"] = False

        if self.options.get_safe("with_jpeg2000") == "openjpeg":
            openjpeg_version = Version(self.dependencies["openjpeg"].ref.version)
            tc.variables["OPENJPEG_MAJOR_VERSION"] = openjpeg_version.major
            tc.variables["OPENJPEG_MINOR_VERSION"] = openjpeg_version.minor
            tc.variables["OPENJPEG_BUILD_VERSION"] = openjpeg_version.patch

        # GUI and platform-native backends.
        tc.variables["WITH_FRAMEBUFFER"] = self.options.get_safe("with_framebuffer", False)
        tc.variables["WITH_FRAMEBUFFER_XVFB"] = self.options.get_safe("with_framebuffer_xvfb", False)
        tc.variables["WITH_GTK"] = self.options.get_safe("with_gtk", False)
        tc.variables["WITH_GTK_2_X"] = False
        tc.variables["WITH_QT"] = self.options.get_safe("with_qt", False)
        tc.variables["WITH_WAYLAND"] = self.options.get_safe("with_wayland", False)
        tc.variables["WITH_OPENGL"] = self.options.get_safe("with_opengl", False)
        if self.options.shared and self.options.get_safe("with_gtk") and (
            self.options.get_safe("with_qt") or self.options.get_safe("with_wayland")
        ):
            tc.variables["HIGHGUI_PLUGIN_LIST"] = "gtk3"
        tc.variables["WITH_WIN32UI"] = self.options.get_safe("with_win32ui", False)
        tc.variables["WITH_DIRECTX"] = self.options.get_safe("with_directx", False)
        # cl_d3d11_ext.h is not part of Khronos OpenCL-Headers. Upstream only
        # supports this NVIDIA extension through its bundled OpenCL 1.2 headers,
        # which the recipe intentionally replaces with the packaged dependency.
        tc.variables["WITH_OPENCL_D3D11_NV"] = False

        # Video I/O. SDKs without a packaged dependency are explicitly disabled.
        tc.variables["WITH_1394"] = self.options.get_safe("with_1394", False)
        tc.variables["WITH_ARAVIS"] = self.options.get_safe("with_aravis", False)
        tc.variables["WITH_AVFOUNDATION"] = self.options.get_safe("with_avfoundation", False)
        tc.variables["WITH_CAP_IOS"] = self.options.get_safe("with_cap_ios", False)
        tc.variables["WITH_DSHOW"] = self.options.get_safe("with_dshow", False)
        tc.variables["WITH_FFMPEG"] = self.options.get_safe("with_ffmpeg", False)
        tc.variables["WITH_GPHOTO2"] = self.options.get_safe("with_gphoto2", False)
        tc.variables["WITH_GSTREAMER"] = self.options.get_safe("with_gstreamer", False)
        tc.variables["WITH_LIBREALSENSE"] = self.options.get_safe("with_librealsense", False)
        tc.variables["WITH_MFX"] = False
        tc.variables["WITH_MSMF"] = self.options.get_safe("with_msmf", False)
        tc.variables["WITH_MSMF_DXVA"] = self.options.get_safe("with_msmf_dxva", False)
        tc.variables["WITH_OPENNI"] = False
        tc.variables["WITH_OPENNI2"] = self.options.get_safe("with_openni2", False)
        tc.variables["WITH_PVAPI"] = False
        tc.variables["WITH_UEYE"] = False
        tc.variables["WITH_V4L"] = self.options.get_safe("with_v4l", False)
        tc.variables["WITH_VA"] = self.options.get_safe("with_va", False)
        tc.variables["WITH_VA_INTEL"] = self.options.get_safe("with_va_intel", False)
        tc.variables["WITH_XIMEA"] = False
        tc.variables["WITH_XINE"] = False
        tc.variables["WITH_ANDROID_MEDIANDK"] = self.options.get_safe("with_android_mediandk", False) and android_api > 20
        tc.variables["WITH_ANDROID_NATIVE_CAMERA"] = self.options.get_safe("with_android_native_camera", False) and android_api > 23
        tc.variables["WITH_OBSENSOR"] = self.options.get_safe("with_obsensor", False)
        tc.variables["OBSENSOR_USE_ORBBEC_SDK"] = False

        if self.options.get_safe("with_ffmpeg"):
            tc.variables["OPENCV_FFMPEG_SKIP_BUILD_CHECK"] = True
            tc.variables["OPENCV_FFMPEG_SKIP_DOWNLOAD"] = True
            tc.variables["OPENCV_FFMPEG_USE_FIND_PACKAGE"] = "FFmpeg"
            tc.variables["OPENCV_INSTALL_FFMPEG_DOWNLOAD_SCRIPT"] = False
            tc.variables["OPENCV_FFMPEG_ENABLE_LIBAVDEVICE"] = self.options.get_safe(
                "with_ffmpeg_libavdevice", False
            )
            ffmpeg_libraries = []
            for component in ("avcodec", "avdevice", "avformat", "avutil", "swscale"):
                if component == "avdevice" and not self.options.get_safe("with_ffmpeg_libavdevice"):
                    continue
                if component == "avutil" or self.dependencies["ffmpeg"].options.get_safe(component):
                    ffmpeg_libraries.append(f"ffmpeg::{component}")
                    component_version = self.dependencies["ffmpeg"].cpp_info.components[component].get_property("component_version")
                    tc.variables[f"FFMPEG_lib{component}_VERSION"] = component_version
            tc.variables["FFMPEG_LIBRARIES"] = ";".join(ffmpeg_libraries)

        if self.options.get_safe("with_openni2"):
            tc.variables["OPENNI2_REQUIRED"] = "REQUIRED"

        if self.options.get_safe("with_va"):
            tc.variables["VA_INCLUDE_DIR"] = self.dependencies["libva"].cpp_info.includedir.replace("\\", "/")
            tc.variables["VA_LIBRARIES"] = "libva::libva"

        # Remaining optional external module integrations.
        tc.variables["WITH_CLP"] = self.options.get_safe("with_clp", False)
        tc.variables["WITH_VTK"] = self.options.get_safe("viz", False)
        tc.variables["WITH_TESSERACT"] = (
            self.options.get_safe("text", False)
            and self.options.get_safe("with_tesseract", False)
        )
        tc.variables["WITH_UNIFONT"] = self.options.get_safe("with_unifont", False)
        unifont_url = Path(self.source_folder, ".conan", "unifont").resolve().as_uri()
        tc.variables["OPENCV_UNIFONT_URL"] = f"{unifont_url}/"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Ceres"] = not self.options.get_safe("with_ceres", False)
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Iconv"] = not self.options.get_safe("with_iconv", False)

        # Options declared by opencv_contrib modules. G-API moved from the main
        # tree to contrib in 5.0, but its ADE dependency remains mandatory when
        # that module is selected.
        tc.variables["WITH_ADE"] = self.options.get_safe("gapi", False)
        tc.variables["WITH_FREETYPE"] = self.options.get_safe("with_freetype", False)
        tc.variables["WITH_GAPI_ONEVPL"] = False
        tc.variables["WITH_OAK"] = False
        tc.variables["WITH_PLAIDML"] = False
        tc.variables["WITH_JULIA"] = False
        tc.variables["WITH_MATLAB"] = False

        # Selected OpenCV modules.
        tc.variables["BUILD_opencv_world"] = self.options.world
        tc.variables["BUILD_opencv_core"] = True
        for module in OPENCV_MAIN_MODULES_OPTIONS:
            tc.variables[f"BUILD_opencv_{module}"] = self.options.get_safe(module, False)
        if any(self.options.get_safe(module) for module in OPENCV_EXTRA_MODULES_OPTIONS) or self.options.get_safe("with_cuda"):
            tc.variables["OPENCV_EXTRA_MODULES_PATH"] = self._extra_modules_folder.replace("\\", "/")
        tc.variables["BUILD_opencv_cudev"] = self.options.get_safe("with_cuda", False)
        for module in OPENCV_EXTRA_MODULES_OPTIONS:
            tc.variables[f"BUILD_opencv_{module}"] = self.options.get_safe(module, False)
        # Keep their contrib modules disabled along with the integrations above.
        tc.variables["BUILD_opencv_cannops"] = False
        tc.variables["BUILD_opencv_fastcv"] = False
        # cnn_3dobj requires an obsolete custom Caffe fork; Caffe support is not planned.
        tc.variables["BUILD_opencv_cnn_3dobj"] = False

        tc.variables["OPENCV_ENABLE_NONFREE"] = self.options.nonfree
        if self.options.cpu_baseline or self.options.cpu_baseline == "":
            tc.variables["CPU_BASELINE"] = self.options.cpu_baseline
        if self.options.cpu_dispatch or self.options.cpu_dispatch == "":
            tc.variables["CPU_DISPATCH"] = self.options.cpu_dispatch

        tc.variables["ENABLE_PIC"] = self.options.get_safe("fPIC", True)
        tc.variables["ENABLE_CONFIG_VERIFICATION"] = True
        tc.variables["ENABLE_DELAYLOAD"] = False
        tc.variables["CV_TRACE"] = self.options.with_itt
        if self._is_cl_like:
            tc.variables["BUILD_WITH_STATIC_CRT"] = self._is_cl_like_static_runtime
        if self.settings.os == "Android":
            tc.variables["BUILD_ANDROID_EXAMPLES"] = False
            tc.variables["BUILD_ANDROID_PROJECTS"] = False
        tc.variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.generate()

        deps = CMakeDeps(self)
        # Names expected by OpenCV's config-mode find_package() calls.
        deps.set_property("ffmpeg", "cmake_file_name", "FFmpeg")
        if self.options.get_safe("with_flatbuffers"):
            # OpenCV's detector uses the canonical header target regardless of
            # whether FlatBuffers also packages its compiled library as shared.
            deps.set_property("flatbuffers", "cmake_target_name", "flatbuffers::flatbuffers")
        deps.set_property("ittapi", "cmake_file_name", "ITT")
        deps.set_property("libjpeg-meta", "cmake_file_name", "JPEG")
        deps.set_property("libjpeg-meta", "cmake_target_name", "JPEG::JPEG")
        deps.set_property("libjxl", "cmake_file_name", "JPEGXL")
        deps.set_property("openni2", "cmake_file_name", "OPENNI2")
        if self.options.get_safe("with_opengl"):
            deps.set_property("opengl", "cmake_file_name", "OpenGL")
            deps.set_property("opengl", "cmake_target_name", "OpenGL::GL")
            deps.set_property("opengl", "cmake_extra_variables", {
                "OPENGL_FOUND": True,
                "OPENGL_LIBRARIES": "OpenGL::GL",
            })
        if self.options.get_safe("with_armpl"):
            deps.set_property("armpl", "cmake_file_name", "ARMPL")
            deps.set_property("armpl", "cmake_target_name", "armpl")
        if self.options.get_safe("with_clp"):
            deps.set_property("coin-clp", "cmake_file_name", "Clp")
            deps.set_property("coin-clp::clp", "cmake_target_name", "Coin::Clp")
            deps.set_property("coin-utils", "cmake_target_name", "Coin::CoinUtils")
        if self.options.get_safe("ovis"):
            # OpenCV's OVIS module uses the OgreBites application framework and
            # consumes OGRE_LIBRARIES instead of its imported target directly.
            deps.set_property("ogre", "cmake_extra_variables", {"OGRE_LIBRARIES": "OgreBites"})
        if with_spng:
            # OpenCV hardcodes spng::spng, while libspng's static package normally
            # exports spng::spng_static.
            deps.set_property("libspng", "cmake_file_name", "SPNG")
            deps.set_property("libspng", "cmake_target_name", "spng::spng")
        deps.generate()

        if self._build_depends_on_pkgconfig:
            pc = PkgConfigDeps(self)
            pc.generate()

        if self.options.get_safe("with_cuda"):
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def _patch_sources(self):
        if self.options.get_safe("with_wayland"):
            detect_wayland = os.path.join(self.source_folder, "modules/highgui/cmake/detect_wayland.cmake")
            replace_in_file(self, detect_wayland,
                "ocv_check_modules(WAYLAND_CLIENT wayland-client)",
                textwrap.dedent("""\
                    ocv_check_modules(WAYLAND_CLIENT wayland-client)
                    find_package(wayland REQUIRED CONFIG)
                    set(WAYLAND_CLIENT_LINK_LIBRARIES wayland::wayland-client)
                """).rstrip())
            replace_in_file(self, detect_wayland,
                "ocv_check_modules(WAYLAND_CURSOR wayland-cursor)",
                textwrap.dedent("""\
                    ocv_check_modules(WAYLAND_CURSOR wayland-cursor)
                    set(WAYLAND_CURSOR_LINK_LIBRARIES wayland::wayland-cursor)
                """).rstrip())
            replace_in_file(self, detect_wayland,
                "ocv_check_modules(XKBCOMMON xkbcommon)",
                textwrap.dedent("""\
                    ocv_check_modules(XKBCOMMON xkbcommon)
                    find_package(xkbcommon REQUIRED CONFIG)
                    set(XKBCOMMON_LINK_LIBRARIES xkbcommon::libxkbcommon)
                """).rstrip())

        # Remove disabled contrib modules before configuration so their init hooks
        # cannot probe undeclared dependencies or otherwise affect the build.
        if not self.options.get_safe("with_cuda"):
            rmdir(self, os.path.join(self._extra_modules_folder, "cudev"))
        for module in OPENCV_EXTRA_MODULES_OPTIONS:
            if not self.options.get_safe(module):
                rmdir(self, os.path.join(self._extra_modules_folder, module))
        for module in ("cannops", "cnn_3dobj", "fastcv", "julia", "matlab"):
            rmdir(self, os.path.join(self._extra_modules_folder, module))

        if self.options.get_safe("freetype"):
            freetype_cmake = os.path.join(self._extra_modules_folder, "freetype/CMakeLists.txt")
            replace_in_file(self, freetype_cmake, "ocv_check_modules(FREETYPE freetype2)",
                textwrap.dedent("""\
                    find_package(Freetype REQUIRED CONFIG)
                    set(FREETYPE_FOUND "${Freetype_FOUND}")
                    set(FREETYPE_LIBRARIES Freetype::Freetype)
                """).rstrip())
            replace_in_file(self, freetype_cmake,
                "ocv_check_modules(HARFBUZZ harfbuzz)",
                textwrap.dedent("""\
                    find_package(harfbuzz REQUIRED CONFIG)
                    set(HARFBUZZ_FOUND "${harfbuzz_FOUND}")
                    set(HARFBUZZ_LIBRARIES harfbuzz::harfbuzz)
                """).rstrip())

        if self.options.get_safe("with_qt"):
            replace_in_file(self, os.path.join(self.source_folder, "modules/highgui/CMakeLists.txt"),
                "${Qt${QT_VERSION_MAJOR}${dt_dep}_LIBRARIES}",
                "Qt${QT_VERSION_MAJOR}::${dt_dep}")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        self._extract_cmake_config_module()
        rmdir(self, os.path.join(self.package_folder, "cmake"))

    @property
    def _cmake_components_module_path(self):
        return "share/conan/opencv/conan-opencv-components.cmake"

    def _extract_cmake_config_module(self):
        upstream_config = load(self, os.path.join(self.package_folder, "cmake", "OpenCVConfig.cmake"))
        section_start = upstream_config.index(textwrap.dedent("""\
            # ==============================================================
            #  Form list of modules (components) to find
            # ==============================================================
        """))
        compatibility_start = upstream_config.index(textwrap.dedent("""\
            # ==============================================================
            # Compatibility stuff
            # ==============================================================
        """), section_start)
        lines = upstream_config[section_start:compatibility_start].splitlines()

        # CMakeDeps already creates every component target, including aliases
        # to opencv_world, and maps configurations itself. Keep upstream's
        # component selection and _FOUND variables, but not its target creation.
        component_logic = []
        skipping_targets = False
        skipping_mapping = False
        for line in lines:
            if line.startswith("if(__remap_warnings AND"):
                break
            if line.startswith("  if(OpenCV_SHARED AND"):
                skipping_targets = True
            elif skipping_targets and line.startswith("  if(TARGET ${__cvcomponent})"):
                skipping_targets = False
                skipping_mapping = True
            elif skipping_mapping and line == "  endif()":
                skipping_mapping = False
            elif not skipping_targets and not skipping_mapping:
                component_logic.append(line)

        generated_variables = []
        for variable in (
            "OpenCV_COMPUTE_CAPABILITIES",
            "OpenCV_ANDROID_NATIVE_API_LEVEL",
            "OpenCV_LIB_COMPONENTS",
        ):
            prefix = f"set({variable} "
            generated_variables.extend(
                line for line in upstream_config.splitlines()
                if line.lower().startswith(prefix.lower())
            )

        content = textwrap.dedent("""\
            include(FindPackageHandleStandardArgs)
            get_filename_component(OpenCV_INSTALL_PATH
                "${CMAKE_CURRENT_LIST_DIR}/../../.." REALPATH)
            set(_OpenCV_HANDLE_COMPONENTS_MANUALLY TRUE)
        """)
        if generated_variables:
            content += "\n".join(generated_variables) + "\n"
        content += "\n".join(component_logic)
        content += "\n" + upstream_config[compatibility_start:]
        save(self, os.path.join(self.package_folder, self._cmake_components_module_path), content)

    @staticmethod
    def _cmake_target(module):
        if module in ("correspondence", "multiview", "numeric", "simple_pipeline"):
            return f"opencv.sfm.{module}"
        return f"opencv_{module}"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenCV")
        self.cpp_info.set_property("pkg_config_name", "opencv5")
        self.cpp_info.resdirs = ["share/opencv5"]

        opencv_modules = _opencv_modules(self.options, self.settings)
        if self.options.get_safe("with_qt") and Version(self.dependencies["qt"].ref.version) >= "6":
            if self.options.get_safe("with_opengl"):
                opencv_modules["highgui"]["requires"].append("qt::qtOpenGLWidgets")
            if self.options.get_safe("cvv"):
                opencv_modules["cvv"]["requires"].append("qt::qtCore5Compat")

        internal_components = {}
        if not self.options.shared:
            packaged_libs = set(collect_libs(self))
            parallel_requires = ["openmp::openmp"] if self.options.parallel == "openmp" else []
            if "tegra_hal" in packaged_libs:
                internal_components["tegra_hal"] = (["tegra_hal"], parallel_requires)
            if "armpl_hal" in packaged_libs:
                internal_components["armpl_hal"] = (["armpl_hal"], ["armpl::armpl"] + parallel_requires,)
            ipphal_lib = (
                "ipphald"
                if self.settings.os == "Windows" and self.settings.build_type == "Debug"
                else "ipphal"
            )
            if ipphal_lib in packaged_libs:
                internal_components["ipphal"] = (
                    [ipphal_lib],
                    ["intel-ipp::ipp_iw", "intel-ipp::ippcv", "intel-ipp::ippcc"],
                )
            opencv_modules["core"]["requires"].extend(internal_components)

        v = Version(self.version)
        self.cpp_info.set_property("cmake_extra_variables", {
            "OpenCV_VERSION": str(v),
            "OpenCV_VERSION_MAJOR": int(str(v.major)),
            "OpenCV_VERSION_MINOR": int(str(v.minor)),
            "OpenCV_VERSION_PATCH": int(str(v.patch)),
            "OpenCV_VERSION_TWEAK": 0,
            "OpenCV_VERSION_STATUS": "",
            "OpenCV_SHARED": bool(self.options.shared),
            "OpenCV_USE_MANGLED_PATHS": False,
        })
        self.cpp_info.set_property("cmake_build_modules", [self._cmake_components_module_path])

        windows = self.settings.os in ("Windows", "WindowsStore")
        version = self.version.split(".")
        version = "".join(version) if windows else ""
        debug = "d" if self.settings.build_type == "Debug" and windows else ""
        sfm_helpers = ("correspondence", "multiview", "numeric", "simple_pipeline")

        def _get_libs(module):
            if module in sfm_helpers:
                return [f"opencv.sfm.{module}"]
            return [f"opencv_{module}{version}{debug}"]

        def _add_components(modules):
            world_components = {
                self._cmake_target(module)
                for module, values in modules.items()
                if values.get("is_built") and values.get("is_part_of_world", True)
            }

            def _remap_world(requirements):
                remapped = []
                for requirement in requirements:
                    requirement = "opencv_world" if requirement in world_components else requirement
                    if requirement not in remapped:
                        remapped.append(requirement)
                return remapped

            if self.options.world:
                self.cpp_info.components["opencv_world"].set_property("cmake_target_name", "opencv_world")
                self.cpp_info.components["opencv_world"].libs = _get_libs("world")
                if self.settings.os == "Windows":
                    self.cpp_info.components["opencv_world"].includedirs = ["include"]
                elif self.settings.os == "Neutrino":
                    self.cpp_info.components["opencv_world"].includedirs = ["usr/include/OpenCV/opencv5"]
                else:
                    self.cpp_info.components["opencv_world"].includedirs = ["include/opencv5"]
                world_requires = []
                world_requires_exclude = set()
                world_system_libs = []
                world_frameworks = []

            for module, values in modules.items():
                if not values.get("is_built"):
                    continue
                cmake_target = self._cmake_target(module)
                conan_component = cmake_target
                is_static_component = module in sfm_helpers
                module_requires = values.get("requires", [])
                if self.options.world and not values.get("is_part_of_world", True):
                    module_requires = _remap_world(module_requires)
                module_system_libs = []
                if not self.options.shared or is_static_component:
                    for _condition, _system_libs in values.get("system_libs", []):
                        if _condition:
                            module_system_libs.extend(_system_libs)
                module_frameworks = []
                if not self.options.shared or is_static_component:
                    for _condition, _frameworks in values.get("frameworks", []):
                        if _condition:
                            module_frameworks.extend(_frameworks)

                if self.options.world and values.get("is_part_of_world", True):
                    world_requires.extend(requirement for requirement in module_requires if requirement not in world_requires)
                    world_requires_exclude.add(conan_component)
                    world_system_libs.extend(library for library in module_system_libs if library not in world_system_libs)
                    world_frameworks.extend(framework for framework in module_frameworks if framework not in world_frameworks)
                    if not self.options.shared:
                        # Upstream creates per-module aliases to opencv_world only
                        # for shared builds.
                        continue

                component = self.cpp_info.components[conan_component]
                component.set_property("cmake_target_name", cmake_target)
                if self.settings.os == "Windows":
                    component.includedirs = ["include"]
                elif self.settings.os == "Neutrino":
                    component.includedirs = ["usr/include/OpenCV/opencv5"]
                else:
                    component.includedirs = ["include/opencv5"]

                if self.options.world and values.get("is_part_of_world", True):
                    component.requires = ["opencv_world"]
                else:
                    component.libs = _get_libs(module)
                    component.requires = module_requires
                    component.system_libs = module_system_libs
                    component.frameworks = module_frameworks

            if self.options.world:
                self.cpp_info.components["opencv_world"].requires = [
                    requirement for requirement in world_requires
                    if requirement not in world_requires_exclude
                ]
                self.cpp_info.components["opencv_world"].system_libs = world_system_libs
                self.cpp_info.components["opencv_world"].frameworks = world_frameworks

        _add_components(opencv_modules)

        for name, (libs, requires) in internal_components.items():
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", name)
            component.includedirs = []
            component.libs = libs
            component.requires = requires


def _mandatory_disabled_options(opts, opencv_modules):
    required_by = {}
    pending = [
        (option, option)
        for option, values in opencv_modules.items()
        if not values.get("no_option") and opts.get_safe(option)
    ]
    visited = set()

    while pending:
        base_option, option = pending.pop()
        for mandatory_option in opencv_modules.get(option, {}).get("mandatory_options", []):
            edge = base_option, mandatory_option
            if edge in visited:
                continue
            visited.add(edge)
            required_by.setdefault(mandatory_option, set()).add(base_option)
            pending.append(edge)

    return {
        option: base_options
        for option, base_options in required_by.items()
        if not opts.get_safe(option)
    }


def _opencv_modules(opts, settings):
    def imageformats_deps():
        components = []
        if opts.get_safe("with_avif"):
            components.append("libavif::libavif")
        if opts.get_safe("with_jpeg"):
            components.append("libjpeg-meta::jpeg")
        if opts.get_safe("with_jpegxl"):
            components.append("libjxl::libjxl")
        if opts.get_safe("with_jpeg2000"):
            components.append("{0}::{0}".format(opts.with_jpeg2000))
        if opts.get_safe("with_png") == "libpng":
            components.append("libpng::libpng")
        elif opts.get_safe("with_png") == "libspng":
            components.append("libspng::libspng")
        if opts.get_safe("with_tiff"):
            components.append("libtiff::tiff")
        if opts.get_safe("with_openexr"):
            components.append("openexr::openexr_")
        if opts.get_safe("with_webp"):
            components.append("libwebp::libwebp")
        if opts.get_safe("with_gdal"):
            components.append("gdal::gdal")
        if opts.get_safe("with_gdcm"):
            components.append("gdcm::gdcmMSFF")
        return components

    def itt():
        return ["ittapi::ittnotify"] if opts.with_itt else []

    def dc1394():
        return ["libdc1394::libdc1394"] if opts.get_safe("with_1394") else []

    def aravis():
        return ["aravis::aravis"] if opts.get_safe("with_aravis") else []

    def eigen():
        return ["eigen::eigen"] if opts.get_safe("with_eigen") else []

    def lapack():
        return ["lapack::lapack"] if opts.get_safe("with_lapack") else []

    def clp():
        return ["coin-clp::clp"] if opts.get_safe("with_clp") else []

    def ffmpeg():
        if not opts.get_safe("with_ffmpeg"):
            return []
        components = ["ffmpeg::avcodec", "ffmpeg::avformat", "ffmpeg::avutil", "ffmpeg::swscale"]
        if opts.get_safe("with_ffmpeg_libavdevice"):
            components.append("ffmpeg::avdevice")
        return components

    def gphoto2():
        return ["libgphoto2::libgphoto2"] if opts.get_safe("with_gphoto2") else []

    def gstreamer():
        if not opts.get_safe("with_gstreamer"):
            return []
        return [
            "gstreamer::gstreamer-base-1.0",
            "gst-plugins-base::gstreamer-app-1.0",
            "gst-plugins-base::gstreamer-riff-1.0",
            "gst-plugins-base::gstreamer-pbutils-1.0",
            "gst-plugins-base::gstreamer-video-1.0",
            "gst-plugins-base::gstreamer-audio-1.0",
        ]

    def openni2():
        return ["openni2::openni2"] if opts.get_safe("with_openni2") else []

    def va():
        return ["libva::libva"] if opts.get_safe("with_va") else []

    def gtk():
        return ["gtk::gtk"] if opts.get_safe("with_gtk") else []

    def ipp():
        if not opts.get_safe("with_ipp"):
            return []
        return ["intel-ipp::ipp_iw", "intel-ipp::ippcv", "intel-ipp::ippcc"]

    def armpl():
        return ["armpl::armpl"] if opts.get_safe("with_armpl") else []

    def cpu_features():
        return ["cpu_features::ndk_compat"] if opts.get_safe("with_cpu_features") else []

    def opencl():
        if opts.get_safe("with_opencl") and str(settings.get_safe("os")) not in ("Macos", "iOS", "watchOS", "tvOS", "visionOS"):
            return ["opencl-icd-loader::opencl-icd-loader"]
        return []

    def clfft():
        return ["clfft::clfft"] if opts.get_safe("with_opencl_clfft") else []

    def clblas():
        return ["clblas::clblas"] if opts.get_safe("with_opencl_clblas") else []

    def librealsense():
        return ["librealsense::realsense2"] if opts.get_safe("with_librealsense") else []

    def parallel():
        if opts.parallel == "openmp":
            return ["openmp::openmp"]
        if opts.parallel == "tbb":
            return ["onetbb::libtbb"]
        return []

    def cudart():
        return ["cudart::cudart_"] if opts.get_safe("with_cuda") else []

    def npp_headers():
        return ["npp::nppc"] if opts.get_safe("with_cuda") else []

    def cublas():
        return ["cublas::cublas_"] if opts.get_safe("with_cublas") else []

    def cufft():
        return ["cufft::cufft_"] if opts.get_safe("with_cufft") else []

    def cudnn():
        return ["cudnn::cudnn_shim"] if opts.get_safe("dnn_cuda") else []

    def nvcodec():
        components = []
        if opts.get_safe("with_nvcuvid"):
            components.append("nvidia-video-codec-sdk::nvcuvid")
        if opts.get_safe("with_nvcuvenc"):
            components.append("nvidia-video-codec-sdk::nvidia-encode")
        return components

    def protobuf():
        return ["protobuf::protobuf"] if opts.get_safe("with_protobuf") else []

    def flatbuffers():
        return ["flatbuffers::flatbuffers"] if opts.get_safe("with_flatbuffers") else []

    def qt():
        if not opts.get_safe("with_qt"):
            return []
        components = [
            "qt::qtCore", "qt::qtGui", "qt::qtWidgets", "qt::qtTest", "qt::qtConcurrent",
        ]
        if opts.get_safe("with_opengl"):
            components.append("qt::qtOpenGL")
        return components

    def qt_cvv():
        if not opts.get_safe("with_qt"):
            return []
        return ["qt::qtCore", "qt::qtGui", "qt::qtWidgets"]

    def tesseract():
        return ["tesseract::tesseract"] if opts.get_safe("with_tesseract") else []

    def wayland():
        if opts.get_safe("with_wayland"):
            return ["wayland::wayland-client", "wayland::wayland-cursor"]
        return []

    def xkbcommon():
        return ["xkbcommon::libxkbcommon"] if opts.get_safe("with_wayland") else []

    def openvino():
        return ["openvino::Runtime"] if opts.get_safe("with_openvino") else []

    def onnxruntime():
        return ["onnxruntime::onnxruntime"] if opts.get_safe("with_onnxruntime") else []

    def opengl():
        return ["opengl::opengl"] if opts.get_safe("with_opengl") else []

    def ceres():
        return ["ceres-solver::ceres"] if opts.get_safe("with_ceres") else []

    def iconv():
        return ["libiconv::libiconv"] if opts.get_safe("with_iconv") else []

    def freetype():
        return ["freetype::freetype"] if opts.get_safe("with_freetype") else []

    def vtk():
        if not opts.get_safe("viz"):
            return []
        return [
            f"vtk::{component}" for component in (
                "FiltersExtraction", "FiltersSources", "FiltersTexture", "IOExport", "IOGeometry", "IOPLY",
                "InteractionStyle", "RenderingCore", "RenderingLOD", "RenderingOpenGL2",
            )
        ]

    def opencv(module):
        return [f"opencv_{module}"] if opts.get_safe(module) else []

    def opencv_cudev():
        return ["opencv_cudev"] if opts.get_safe("with_cuda") else []

    return {
        # Main modules
        "calib": {
            "is_built": opts.calib,
            "mandatory_options": ["flann", "geometry", "imgproc", "objdetect", "stereo"],
            "requires": [
                "opencv_imgproc", "opencv_objdetect", "opencv_flann", "opencv_geometry", "opencv_stereo",
            ] + ipp(),
        },
        "core": {
            "is_built": True,
            "no_option": True,
            "requires": ["zlib-ng::zlib-ng"] + opencv_cudev() + parallel() + eigen() + ipp() + armpl() +
                        cpu_features() + opencl() + clblas() + clfft() + va() + itt() + cudart() +
                        npp_headers() + opengl(),
            "system_libs": [
                (settings.os == "Android", ["dl", "m", "log"]),
                (settings.os == "FreeBSD", ["m", "pthread"]),
                (settings.os == "Linux", ["dl", "m", "pthread", "rt"]),
            ],
            "frameworks": [
                (settings.os == "Macos" and opts.get_safe("with_opencl"), ["OpenCL"]),
            ],
        },
        "dnn": {
            "is_built": opts.get_safe("dnn"),
            "mandatory_options": ["geometry", "imgproc", "with_protobuf"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_geometry"] +
                        cudnn() + cublas() + protobuf() + flatbuffers() + ipp() + openvino() +
                        onnxruntime() + lapack(),
        },
        "features": {
            "is_built": opts.features,
            "mandatory_options": ["geometry", "imgproc"],
            "requires": ["opencv_imgproc", "opencv_geometry"] + opencv("flann") + opencv("dnn") + ipp(),
        },
        "flann": {
            "is_built": opts.flann,
            "requires": ["opencv_core"] + ipp(),
        },
        "geometry": {
            "is_built": opts.geometry,
            "mandatory_options": ["flann"],
            "requires": ["opencv_flann"] + eigen() + lapack() + ipp(),
        },
        "highgui": {
            "is_built": opts.highgui,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_imgproc"] + opencv("imgcodecs") +
                        opencv("videoio") + gtk() + qt() + xkbcommon() + wayland() +
                        opengl() + ipp(),
            "system_libs": [
                (settings.os in ("Windows", "WindowsStore"),
                 ["comctl32", "gdi32", "ole32", "setupapi", "ws2_32"]),
                (settings.os in ("Windows", "WindowsStore") and opts.get_safe("with_win32ui"),
                 ["user32", "gdi32"]),
                (
                    settings.os in ("Windows", "WindowsStore") and settings.arch == "armv8"
                    and opts.get_safe("with_win32ui"),
                    ["comdlg32", "advapi32"],
                ),
            ],
            "frameworks": [
                (settings.os == "Macos" and not opts.get_safe("with_qt"), ["Cocoa"]),
            ],
        },
        "imgcodecs": {
            "is_built": opts.imgcodecs,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_imgproc", "zlib-ng::zlib-ng"] + imageformats_deps() + ipp(),
            "frameworks": [
                (str(settings.os) in ("iOS", "visionOS"), ["UIKit"]),
                (str(settings.os) in ("Macos", "watchOS", "tvOS"), ["AppKit"]),
            ],
        },
        "imgproc": {
            "is_built": opts.imgproc,
            "mandatory_options": ["geometry"],
            "requires": ["opencv_core", "opencv_geometry", "zlib-ng::zlib-ng"] + ipp(),
        },
        "objdetect": {
            "is_built": opts.objdetect,
            "mandatory_options": ["features", "geometry", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_features", "opencv_geometry"] +
                        opencv("dnn") + ipp(),
        },
        "photo": {
            "is_built": opts.photo,
            "mandatory_options": ["geometry", "imgproc"],
            "requires": ["opencv_imgproc", "opencv_geometry"] + opencv("cudaarithm") +
                        opencv("cudaimgproc") + ipp(),
        },
        "ptcloud": {
            "is_built": opts.ptcloud,
            "mandatory_options": ["flann", "geometry", "imgproc"],
            "requires": ["opencv_geometry", "opencv_imgproc", "opencv_flann"] +
                        eigen() + lapack() + ipp(),
        },
        "stereo": {
            "is_built": opts.stereo,
            "mandatory_options": ["geometry", "imgproc"],
            "requires": ["opencv_imgproc", "opencv_geometry"] + ipp(),
        },
        "stitching": {
            "is_built": opts.stitching,
            "mandatory_options": ["features", "flann", "geometry", "imgproc"],
            "requires": ["opencv_imgproc", "opencv_features", "opencv_geometry", "opencv_flann"] +
                        opencv("xfeatures2d") + opencv("cudaarithm") + opencv("cudawarping") +
                        opencv("cudafeatures2d") + opencv("cudalegacy") + opencv("cudaimgproc") + ipp(),
        },
        "video": {
            "is_built": opts.video,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_imgproc"] + opencv("geometry") + opencv("features") +
                        opencv("dnn") + ipp(),
        },
        "videoio": {
            "is_built": opts.videoio,
            "mandatory_options": ["imgcodecs", "imgproc"],
            "requires": ["opencv_imgproc", "opencv_imgcodecs"] + dc1394() + aravis() + ffmpeg() +
                        gphoto2() + gstreamer() + librealsense() + openni2() + ipp(),
            "system_libs": [
                (
                    settings.os == "Android" and int(str(settings.os.api_level)) > 20
                    and opts.get_safe("with_android_mediandk"),
                    ["android", "log", "mediandk"],
                ),
                (
                    settings.os == "Android" and int(str(settings.os.api_level)) > 23
                    and opts.get_safe("with_android_native_camera"),
                    ["android", "log", "camera2ndk"],
                ),
            ],
            "frameworks": [
                (
                    settings.os == "iOS" and opts.get_safe("with_avfoundation"),
                    ["AVFoundation", "QuartzCore"],
                ),
                (
                    str(settings.os) in ("Macos", "watchOS", "tvOS", "visionOS")
                    and opts.get_safe("with_avfoundation"),
                    [
                        "Cocoa", "Accelerate", "AVFoundation", "CoreGraphics",
                        "CoreMedia", "CoreVideo", "QuartzCore",
                    ],
                ),
                (
                    settings.os == "iOS" and opts.get_safe("with_cap_ios"),
                    [
                        "Accelerate", "AVFoundation", "CoreGraphics", "CoreImage",
                        "CoreMedia", "CoreVideo", "QuartzCore", "UIKit",
                    ],
                ),
            ],
        },

        # Contrib modules
        "alphamat": {
            "is_built": opts.alphamat,
            "mandatory_options": ["with_eigen", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc"] + eigen() + ipp(),
        },
        "bgsegm": {
            "is_built": opts.bgsegm,
            "mandatory_options": ["geometry", "imgproc", "video"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_video", "opencv_geometry"] + ipp(),
        },
        "bioinspired": {
            "is_built": opts.bioinspired,
            "requires": ["opencv_core"] + opencv("highgui") + ipp(),
        },
        "ccalib": {
            "is_built": opts.ccalib,
            "mandatory_options": [
                "calib", "features", "geometry", "highgui", "imgcodecs", "imgproc", "objdetect", "xfeatures2d",
            ],
            "requires": [
                "opencv_core", "opencv_imgproc", "opencv_geometry", "opencv_calib", "opencv_objdetect",
                "opencv_features", "opencv_xfeatures2d", "opencv_highgui", "opencv_imgcodecs",
            ] + ipp(),
        },
        "cudaarithm": {
            "is_built": opts.cudaarithm,
            "mandatory_options": ["with_cuda"],
            "requires": [
                "opencv_core", "opencv_cudev", "npp::nppial", "npp::nppc", "npp::nppitc",
                "npp::nppig", "npp::nppist", "npp::nppidei",
            ] + ipp() + cublas() + cufft(),
        },
        "cudabgsegm": {
            "is_built": opts.cudabgsegm,
            "mandatory_options": ["with_cuda", "video"],
            "requires": ["opencv_video"] + cudart() + ipp(),
        },
        "cudacodec": {
            "is_built": opts.cudacodec,
            "mandatory_options": ["with_cuda", "videoio", "cudaarithm", "cudawarping"] +
                                 (["cudaimgproc"] if opts.get_safe("with_nvcuvenc") else []),
            "requires": ["opencv_core", "opencv_videoio", "opencv_cudaarithm", "opencv_cudawarping"] +
                        (["opencv_cudaimgproc"] if opts.get_safe("with_nvcuvenc") else []) +
                        cudart() + ipp() + nvcodec(),
        },
        "cudafeatures2d": {
            "is_built": opts.cudafeatures2d,
            "mandatory_options": ["with_cuda", "features", "cudafilters", "cudawarping"],
            "requires": ["opencv_features", "opencv_cudafilters", "opencv_cudawarping"] + ipp(),
        },
        "cudafilters": {
            "is_built": opts.cudafilters,
            "mandatory_options": ["with_cuda", "imgproc", "cudaarithm"],
            "requires": ["opencv_imgproc", "opencv_cudaarithm", "npp::nppif", "npp::nppim"] + ipp(),
        },
        "cudaimgproc": {
            "is_built": opts.cudaimgproc,
            "mandatory_options": ["with_cuda", "imgproc"],
            "requires": [
                "opencv_imgproc", "opencv_cudev", "npp::nppial", "npp::nppist", "npp::nppicc",
                "npp::nppidei",
            ] + opencv("cudaarithm") +
                        opencv("cudafilters") + opencv("geometry") + ipp(),
        },
        "cudalegacy": {
            "is_built": opts.cudalegacy,
            "mandatory_options": ["with_cuda", "geometry", "video"],
            "requires": ["opencv_core", "opencv_geometry", "opencv_video"] + opencv("objdetect") +
                        opencv("xobjdetect") + opencv("imgproc") + opencv("stereo") + opencv("calib") +
                        opencv("cudaarithm") + opencv("cudafilters") + opencv("cudaimgproc") + ipp(),
        },
        "cudaobjdetect": {
            "is_built": opts.cudaobjdetect,
            "mandatory_options": ["with_cuda", "objdetect", "xobjdetect", "cudaarithm", "cudawarping"],
            "requires": [
                "opencv_objdetect", "opencv_xobjdetect", "opencv_cudaarithm", "opencv_cudawarping",
            ] + opencv("cudalegacy") + ipp(),
        },
        "cudaoptflow": {
            "is_built": opts.cudaoptflow,
            "mandatory_options": [
                "with_cuda", "video", "optflow", "cudaarithm", "cudaimgproc", "cudawarping", "cudafeatures2d",
            ],
            "requires": [
                "opencv_video", "opencv_optflow", "opencv_cudaarithm", "opencv_cudawarping",
                "opencv_cudaimgproc", "opencv_cudafeatures2d",
            ] + opencv("cudalegacy") + ipp(),
        },
        "cudastereo": {
            "is_built": opts.cudastereo,
            "mandatory_options": ["with_cuda", "geometry", "stereo"],
            "requires": ["opencv_geometry", "opencv_stereo", "opencv_cudev"] + ipp(),
        },
        "cudawarping": {
            "is_built": opts.cudawarping,
            "mandatory_options": ["with_cuda", "geometry", "imgproc"],
            "requires": [
                "opencv_core", "opencv_imgproc", "opencv_geometry", "opencv_cudev",
                "npp::nppial", "npp::nppig",
            ] + ipp(),
        },
        "cudev": {
            "is_built": opts.get_safe("with_cuda"),
            "no_option": True,
            "requires": cudart() + ipp(),
        },
        "cvv": {
            "is_built": opts.cvv,
            "mandatory_options": ["with_qt", "features", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_features"] + qt_cvv() + ipp(),
        },
        "datasets": {
            "is_built": opts.datasets,
            "mandatory_options": ["flann", "imgcodecs", "ml"],
            "requires": ["opencv_core", "opencv_imgcodecs", "opencv_ml", "opencv_flann"] +
                        opencv("text") + ipp(),
        },
        "dnn_objdetect": {
            "is_built": opts.dnn_objdetect,
            "mandatory_options": ["dnn", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_dnn"] + opencv("highgui") +
                        opencv("imgcodecs") + ipp(),
        },
        "dnn_superres": {
            "is_built": opts.dnn_superres,
            "mandatory_options": ["dnn", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_dnn"] + opencv("quality") + ipp(),
        },
        "dpm": {
            "is_built": opts.dpm,
            "mandatory_options": ["imgproc", "objdetect"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_objdetect"] + opencv("highgui") + ipp(),
        },
        "face": {
            "is_built": opts.face,
            "mandatory_options": ["geometry", "imgproc", "photo", "xobjdetect"],
            "requires": [
                "opencv_core", "opencv_imgproc", "opencv_xobjdetect", "opencv_geometry", "opencv_photo",
            ] + ipp(),
        },
        "freetype": {
            "is_built": opts.freetype,
            "mandatory_options": ["imgproc", "with_freetype"],
            "requires": ["opencv_core", "opencv_imgproc", "freetype::freetype", "harfbuzz::harfbuzz"] + ipp(),
        },
        "fuzzy": {
            "is_built": opts.fuzzy,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_imgproc", "opencv_core"] + ipp(),
        },
        "gapi": {
            "is_built": opts.gapi,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_imgproc", "ade::ade"] + opencv("video") + opencv("stereo") +
                        openvino() + onnxruntime() + gstreamer() + va() + itt() + freetype(),
            "system_libs": [
                (settings.os in ("Windows", "WindowsStore"), ["ws2_32", "wsock32"]),
            ],
        },
        "hdf": {
            "is_built": opts.hdf,
            "requires": ["opencv_core", "hdf5::hdf5"] + ipp(),
        },
        "hfs": {
            "is_built": opts.hfs,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
        },
        "img_hash": {
            "is_built": opts.img_hash,
            "is_part_of_world": False,
            "mandatory_options": ["geometry", "imgproc"],
            "requires": ["opencv_imgproc", "opencv_geometry", "opencv_core"] + ipp(),
        },
        "intensity_transform": {
            "is_built": opts.intensity_transform,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
        },
        "line_descriptor": {
            "is_built": opts.line_descriptor,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_imgproc"] + opencv("features") + ipp(),
        },
        "ml": {
            "is_built": opts.ml,
            "mandatory_options": ["geometry"],
            "requires": ["opencv_core", "opencv_geometry"] + ipp(),
        },
        "optflow": {
            "is_built": opts.optflow,
            "mandatory_options": ["features", "flann", "geometry", "imgcodecs", "imgproc", "video", "ximgproc"],
            "requires": [
                "opencv_core", "opencv_imgproc", "opencv_features", "opencv_geometry", "opencv_video",
                "opencv_ximgproc", "opencv_imgcodecs", "opencv_flann",
            ] + ipp(),
        },
        "ovis": {
            "is_built": opts.ovis,
            "mandatory_options": ["geometry", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_geometry", "ogre::Main"] + ipp(),
        },
        "phase_unwrapping": {
            "is_built": opts.phase_unwrapping,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
        },
        "plot": {
            "is_built": opts.plot,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
        },
        "quality": {
            "is_built": opts.quality,
            "mandatory_options": ["imgproc", "ml"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_ml"] + ipp(),
        },
        "rapid": {
            "is_built": opts.rapid,
            "mandatory_options": ["geometry", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_geometry"] + ipp(),
        },
        "reg": {
            "is_built": opts.reg,
            "mandatory_options": ["imgproc"],
            "requires": ["opencv_imgproc", "opencv_core"] + ipp(),
        },
        "rgbd": {
            "is_built": opts.rgbd,
            "mandatory_options": ["geometry", "imgproc", "ptcloud"],
            "requires": ["opencv_core", "opencv_geometry", "opencv_imgproc", "opencv_ptcloud"] +
                        opencv("viz") + eigen() + ipp() + opengl(),
        },
        "saliency": {
            "is_built": opts.saliency,
            "mandatory_options": ["features", "imgproc"],
            "requires": ["opencv_imgproc", "opencv_features"] + ipp(),
        },
        "sfm": {
            "is_built": opts.sfm,
            "is_part_of_world": False,
            "mandatory_options": ["with_eigen", "features", "geometry", "imgcodecs", "xfeatures2d"],
            "requires": [
                "opencv_core", "opencv_geometry", "opencv_features", "opencv_xfeatures2d", "opencv_imgcodecs",
                "opencv.sfm.correspondence", "opencv.sfm.multiview", "opencv.sfm.numeric",
                "glog::glog", "gflags::gflags",
            ] + (["opencv.sfm.simple_pipeline"] if opts.get_safe("with_ceres") else []) +
                eigen() + ipp(),
        },
        "shape": {
            "is_built": opts.shape,
            "mandatory_options": ["geometry", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_geometry"] + ipp(),
        },
        "signal": {
            "is_built": opts.signal,
            "requires": ["opencv_core"] + ipp(),
        },
        "structured_light": {
            "is_built": opts.structured_light,
            "mandatory_options": ["calib", "geometry", "imgproc", "phase_unwrapping", "stereo"],
            "requires": [
                "opencv_core", "opencv_imgproc", "opencv_geometry", "opencv_stereo", "opencv_calib",
                "opencv_phase_unwrapping",
            ] + opencv("viz") + ipp(),
        },
        "superres": {
            "is_built": opts.get_safe("superres"),
            "mandatory_options": ["imgproc", "optflow", "video"],
            "requires": ["opencv_imgproc", "opencv_video", "opencv_optflow"] + opencv("videoio") +
                        opencv("cudaarithm") + opencv("cudafilters") + opencv("cudawarping") +
                        opencv("cudaimgproc") + opencv("cudaoptflow") + opencv("cudacodec") + ipp(),
        },
        "surface_matching": {
            "is_built": opts.surface_matching,
            "mandatory_options": ["flann"],
            "requires": ["opencv_core", "opencv_flann"] + ipp(),
        },
        "text": {
            "is_built": opts.text,
            "mandatory_options": ["dnn", "features", "geometry", "imgproc", "ml"],
            "requires": [
                "opencv_ml", "opencv_imgproc", "opencv_core", "opencv_features", "opencv_geometry", "opencv_dnn",
            ] + tesseract() + ipp(),
        },
        "tracking": {
            "is_built": opts.tracking,
            "mandatory_options": ["imgproc", "video"],
            "requires": ["opencv_imgproc", "opencv_core", "opencv_video"] +
                        opencv("plot") + opencv("dnn") + opencv("datasets") +
                        opencv("highgui") + ipp(),
        },
        "videostab": {
            "is_built": opts.videostab,
            "mandatory_options": ["features", "geometry", "imgproc", "photo", "video"],
            "requires": [
                "opencv_imgproc", "opencv_features", "opencv_video", "opencv_photo", "opencv_geometry",
            ] + opencv("cudafeatures2d") + opencv("cudawarping") + opencv("cudaoptflow") +
                        opencv("videoio") + clp() + ipp(),
        },
        "viz": {
            "is_built": opts.get_safe("viz"),
            "requires": ["opencv_core"] + vtk() + ipp(),
            "frameworks": [
                (settings.os == "Macos", ["Cocoa"]),
            ],
        },
        "wechat_qrcode": {
            "is_built": opts.wechat_qrcode,
            "mandatory_options": ["dnn", "geometry", "imgproc", "objdetect"],
            "requires": [
                "opencv_core", "opencv_geometry", "opencv_imgproc", "opencv_objdetect", "opencv_dnn",
            ] + iconv() + ipp(),
        },
        "xfeatures2d": {
            "is_built": opts.xfeatures2d,
            "mandatory_options": ["features", "geometry", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_features", "opencv_geometry"] +
                        opencv("shape") + opencv("ml") + opencv("cudaarithm") + ipp(),
        },
        "ximgproc": {
            "is_built": opts.ximgproc,
            "mandatory_options": ["geometry", "imgcodecs", "imgproc", "stereo", "video"],
            "requires": [
                "opencv_core", "opencv_imgproc", "opencv_geometry", "opencv_stereo", "opencv_imgcodecs",
                "opencv_video",
            ] + eigen() + ipp(),
        },
        "xobjdetect": {
            "is_built": opts.xobjdetect,
            "mandatory_options": ["features", "imgcodecs", "imgproc"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_imgcodecs", "opencv_features"] + ipp(),
        },
        "xphoto": {
            "is_built": opts.xphoto,
            "mandatory_options": ["imgproc", "photo"],
            "requires": ["opencv_core", "opencv_imgproc", "opencv_photo"] + ipp(),
        },
        "xstereo": {
            "is_built": opts.xstereo,
            "mandatory_options": ["features", "imgproc", "stereo", "tracking"],
            "requires": [
                "opencv_imgproc", "opencv_features", "opencv_core", "opencv_stereo", "opencv_tracking",
            ] + ipp(),
        },

        # Extra installed targets without the opencv_ target/library prefix
        "numeric": {
            "is_built": opts.sfm,
            "is_part_of_world": False,
            "no_option": True,
            "requires": eigen(),
        },
        "correspondence": {
            "is_built": opts.sfm,
            "is_part_of_world": False,
            "no_option": True,
            "requires": ["opencv_imgcodecs", "opencv.sfm.multiview", "glog::glog"] + eigen(),
        },
        "multiview": {
            "is_built": opts.sfm,
            "is_part_of_world": False,
            "no_option": True,
            "requires": ["opencv.sfm.numeric", "glog::glog"] + ceres() + eigen(),
        },
        "simple_pipeline": {
            "is_built": opts.sfm and opts.get_safe("with_ceres"),
            "is_part_of_world": False,
            "no_option": True,
            "requires": ["opencv.sfm.multiview"] + ceres(),
        },
    }
