import os
import re
import textwrap
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc, msvc_runtime_flag
from conan.tools.scm import Version

required_conan_version = ">=2.1"


OPENCV_MAIN_MODULES_OPTIONS = (
    "calib3d",
    "dnn",
    "features2d",
    "flann",
    "gapi",
    "highgui",
    "imgcodecs",
    "imgproc",
    "ml",
    "objdetect",
    "photo",
    "stitching",
    "video",
    "videoio",
)

OPENCV_EXTRA_MODULES_OPTIONS = (
    "alphamat",
    "aruco",
    "barcode",
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
    "hdf",
    "hfs",
    "img_hash",
    "intensity_transform",
    "line_descriptor",
    "mcc",
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
    "stereo",
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
        # global options
        "parallel": [False, "tbb", "openmp"],
        "neon": [True, False],
        "with_ipp": [False, "intel-ipp", "opencv-icv"],
        "with_eigen": [True, False],
        "with_lapack": [True, False],
        "with_opencl": [True, False],
        "with_cuda": [True, False],
        "with_cublas": [True, False],
        "with_cufft": [True, False],
        "cpu_baseline": [None, "ANY"],
        "cpu_dispatch": [None, "ANY"],
        "with_itt": [True, False],
        "world": [True, False],
        "nonfree": [True, False],
        # dnn module options
        "with_flatbuffers": [True, False],
        "with_protobuf": [True, False],
        "with_vulkan": [True, False],
        "with_openvino": [True, False],
        "dnn_cuda": [True, False],
        # highgui module options
        "with_framebuffer": [True, False],
        "with_gtk": [True, False],
        "with_qt": [True, False],
        "with_wayland": [True, False],
        # imgcodecs module options
        "with_avif": [True, False],
        "with_jpeg": [True, False],
        "with_jpegxl": [True, False],
        "with_jpeg2000": [False, "jasper", "openjpeg"],
        "with_png": [True, False],
        "with_tiff": [True, False],
        "with_openexr": [True, False],
        "with_webp": [True, False],
        "with_gdal": [True, False],
        "with_gdcm": [True, False],
        "with_imgcodec_hdr": [True, False],
        "with_imgcodec_pfm": [True, False],
        "with_imgcodec_pxm": [True, False],
        "with_imgcodec_sunraster": [True, False],
        "with_msmf": [True, False],
        "with_msmf_dxva": [True, False],
        # objdetect module options
        "with_quirc": [True, False],
        # videoio module options
        "with_1394": [True, False],
        "with_aravis": [True, False],
        "with_ffmpeg": [True, False],
        "with_gphoto2": [True, False],
        "with_gstreamer": [True, False],
        "with_librealsense": [True, False],
        "with_openni2": [True, False],
        "with_va": [True, False],
        "with_v4l": [True, False],
        # text module options
        "with_tesseract": [True, False],
        # videostab module options
        "with_clp": [True, False],

        # Force all main module options to True
        "build_all_base": [True, False],
        # Force all contrib module options to True
        "build_all_contrib": [True, False],
    }
    options.update({_name: [True, False] for _name in OPENCV_MAIN_MODULES_OPTIONS})
    options.update({_name: [True, False] for _name in OPENCV_EXTRA_MODULES_OPTIONS})

    default_options = {
        "shared": False,
        "fPIC": True,
        # global options
        "parallel": "openmp",
        "neon": True,
        "with_ipp": False,
        "with_eigen": True,
        "with_lapack": False,
        "with_opencl": False,
        "with_cuda": False,
        "with_cublas": False,
        "with_cufft": False,
        "cpu_baseline": None,
        "cpu_dispatch": None,
        "with_itt": False,
        "world": False,
        "nonfree": False,
        # dnn module options
        "with_flatbuffers": False,
        "with_protobuf": False,
        "with_vulkan": False,
        "with_openvino": False,
        "dnn_cuda": False,
        # highgui module options
        "with_framebuffer": False,
        "with_gtk": False,
        "with_qt": True,
        "with_wayland": False,
        # imgcodecs module options
        "with_avif": False,
        "with_jpeg": True,
        "with_jpegxl": False,
        "with_jpeg2000": False,
        "with_png": True,
        "with_tiff": True,
        "with_openexr": False,
        "with_webp": True,
        "with_gdal": False,
        "with_gdcm": False,
        "with_imgcodec_hdr": True,
        "with_imgcodec_pfm": True,
        "with_imgcodec_pxm": True,
        "with_imgcodec_sunraster": True,
        "with_msmf": True,
        "with_msmf_dxva": True,
        # objdetect module options
        "with_quirc": False,
        # videoio module options
        "with_1394": False,
        "with_aravis": False,
        "with_ffmpeg": True,
        "with_gphoto2": False,
        "with_gstreamer": False,
        "with_librealsense": False,
        "with_openni2": False,
        "with_va": False,
        "with_v4l": True,
        # text module options
        "with_tesseract": True,
        # videostab module options
        "with_clp": False,

        # main modules - enable the more lightweight ones by default
        "calib3d": True,
        "dnn": False,
        "features2d": True,
        "flann": True,
        "gapi": False,
        "highgui": False,
        "imgcodecs": True,
        "imgproc": True,
        "ml": False,
        "objdetect": False,
        "photo": True,
        "stitching": True,
        "video": True,
        "videoio": False,

        "build_all_base": False,
        "build_all_contrib": False,
    }
    default_options.update({_name: False for _name in OPENCV_EXTRA_MODULES_OPTIONS})

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
    def _build_depends_on_pkgconfig(self):
        return (
            self.options.get_safe("with_clp")
            or self.options.get_safe("with_1394")
            or self.options.get_safe("with_aravis")
            or self.options.get_safe("with_gphoto2")
            or self.options.get_safe("with_gstreamer")
            or self.options.get_safe("with_wayland")
        )

    @property
    def _is_apple_device_os(self):
        return is_apple_os(self) and self.settings.os != "Macos"

    @property
    def _has_jpegxl_option(self):
        return Version(self.version) >= "4.11.0"

    @property
    def _has_with_jpeg2000_option(self):
        return not self._is_apple_device_os

    @property
    def _has_with_tiff_option(self):
        return not self._is_apple_device_os

    @property
    def _has_with_ffmpeg_option(self):
        return self.settings.os not in ["WindowsStore"] and not self._is_apple_device_os

    @property
    def _has_with_gstreamer_option(self):
        return self.settings.os not in ["Android", "WindowsStore"] and not self._is_apple_device_os

    @property
    def _has_with_1394_option(self):
        return self.settings.os not in ["Android", "Windows", "WindowsStore"] and not self._is_apple_device_os

    @property
    def _has_with_aravis_option(self):
        return self.settings.os not in ["Android", "Windows", "WindowsStore"] and not self._is_apple_device_os

    @property
    def _has_with_gphoto2_option(self):
        return self.settings.os not in ["Android", "Windows", "WindowsStore"] and not self._is_apple_device_os

    @property
    def _has_with_openni2_option(self):
        return self.settings.os not in ["Android", "Windows", "WindowsStore"] and not self._is_apple_device_os

    @property
    def _has_with_va_option(self):
        return self.settings.os in ["Linux", "FreeBSD"]

    @property
    def _has_superres_option(self):
        return not self._is_apple_device_os

    @property
    def _has_alphamat_option(self):
        return Version(self.version) >= "4.3.0"

    @property
    def _has_intensity_transform_option(self):
        return Version(self.version) >= "4.3.0"

    @property
    def _has_rapid_option(self):
        return Version(self.version) >= "4.3.0"

    @property
    def _has_mcc_option(self):
        return Version(self.version) >= "4.5.0"

    @property
    def _has_wechat_qrcode_option(self):
        return Version(self.version) >= "4.5.2"

    @property
    def _has_barcode_option(self):
        return "4.5.3" <= Version(self.version) < "4.8.0"

    @property
    def _has_openvino_option(self):
        return Version(self.version) >= "4.10.0"

    @property
    def _has_framebuffer_option(self):
        return Version(self.version) >= "4.11.0" and self.settings.os in ["Linux", "FreeBSD"]

    @property
    def _has_with_wayland_option(self):
        return Version(self.version) >= "4.7.0" and self.settings.os in ["Linux", "FreeBSD"]

    @property
    def _has_with_avif_option(self):
        return Version(self.version) >= "4.8.0"

    @property
    def _has_with_flatbuffers_option(self):
        return Version(self.version) >= "4.8.0"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.with_gtk
            del self.options.with_v4l
        if self.settings.os == "Android" or self._is_apple_device_os:
            del self.options.with_opencl
        if self.settings.os != "Windows":
            del self.options.with_msmf
            del self.options.with_msmf_dxva

        if self._has_with_ffmpeg_option:
            # Following the packager choice, ffmpeg is enabled by default when
            # supported, except on Android. See
            # https://github.com/opencv/opencv/blob/39c3334147ec02761b117f180c9c4518be18d1fa/CMakeLists.txt#L266-L268
            self.options.with_ffmpeg = self.settings.os != "Android"
        else:
            del self.options.with_ffmpeg

        if not self._has_jpegxl_option:
            del self.options.with_jpegxl
        if not self._has_with_jpeg2000_option:
            del self.options.with_jpeg2000

        if "arm" not in str(self.settings.arch) or Version(self.version) >= "4.11.0":
            del self.options.neon
        if not self._has_with_tiff_option:
            del self.options.with_tiff
        if not self._has_with_gstreamer_option:
            del self.options.with_gstreamer
        if not self._has_with_1394_option:
            del self.options.with_1394
        if not self._has_with_aravis_option:
            del self.options.with_aravis
        if not self._has_with_gphoto2_option:
            del self.options.with_gphoto2
        if not self._has_with_openni2_option:
            del self.options.with_openni2
        if not self._has_with_va_option:
            del self.options.with_va
        if not self._has_superres_option:
            del self.options.superres
        if not self._has_alphamat_option:
            del self.options.alphamat
        if not self._has_intensity_transform_option:
            del self.options.intensity_transform
        if not self._has_rapid_option:
            del self.options.rapid
        if not self._has_mcc_option:
            del self.options.mcc
        if not self._has_wechat_qrcode_option:
            del self.options.wechat_qrcode
        if not self._has_barcode_option:
            del self.options.barcode
        if not self._has_framebuffer_option:
            del self.options.with_framebuffer
        if not self._has_with_wayland_option:
            del self.options.with_wayland
        if not self._has_with_avif_option:
            del self.options.with_avif
        if not self._has_with_flatbuffers_option:
            del self.options.with_flatbuffers

        # Conditional default options
        if self._is_mingw:
            # These options are visible for Windows, but upstream disables them
            # by default for MinGW (actually it would fail otherwise)
            self.options.with_msmf = False
            self.options.with_msmf_dxva = False
        if self.settings.os == "Linux":
            # Use Wayland by default, but fallback to GTK for old OpenCV versions.
            # gtk/system is problematic for this recpe, there might be side effects
            # in a big dependency graph
            if not self._has_with_wayland_option:
                self.options.with_gtk = True

        if is_msvc(self) and self.settings.arch == "armv8":
            # See https://github.com/opencv/opencv/issues/25052
            #     https://github.com/opencv/opencv/pull/24698#issuecomment-1858023908
            self.options.cpu_baseline = "NEON"
            self.options.cpu_dispatch = ""

    @property
    def _opencv_modules(self):
        def imageformats_deps():
            components = []
            if self.options.get_safe("with_avif"):
                components.append("libavif::libavif")
            if self.options.get_safe("with_jpeg"):
                components.append("libjpeg-meta::jpeg")
            if self.options.get_safe("with_jpegxl"):
                components.append("libjxl::libjxl")
            if self.options.get_safe("with_jpeg2000"):
                components.append("{0}::{0}".format(self.options.with_jpeg2000))
            if self.options.get_safe("with_png"):
                components.append("libpng::libpng")
            if self.options.get_safe("with_tiff"):
                components.append("libtiff::tiff")
            if self.options.get_safe("with_openexr"):
                components.append("openexr::openexr")
            if self.options.get_safe("with_webp"):
                components.append("libwebp::libwebp")
            if self.options.get_safe("with_gdal"):
                components.append("gdal::gdal")
            if self.options.get_safe("with_gdcm"):
                components.append("gdcm::gdcm")
            return components

        def itt():
            return ["ittapi::ittapi"] if self.options.with_itt else []

        def dc1394():
            return ["libdc1394::libdc1394"] if self.options.get_safe("with_1394") else []

        def aravis():
            return ["aravis::aravis"] if self.options.get_safe("with_aravis") else []

        def eigen():
            return ["eigen::eigen"] if self.options.with_eigen else []

        def lapack():
            return ["lapack::lapack"] if self.options.get_safe("with_lapack") else []

        def clp():
            return ["coin-clp::coin-clp"] if self.options.get_safe("with_clp") else []

        def ffmpeg():
            components = []
            if self.options.get_safe("with_ffmpeg"):
                components = ["ffmpeg::avcodec", "ffmpeg::avformat", "ffmpeg::avutil", "ffmpeg::swscale"]
            return components

        def gphoto2():
            return ["libgphoto2::libgphoto2"] if self.options.get_safe("with_gphoto2") else []

        def gstreamer():
            if self.options.get_safe("with_gstreamer"):
                return [
                    "gstreamer::gstreamer-base-1.0",
                    "gst-plugins-base::gstreamer-app-1.0",
                    "gst-plugins-base::gstreamer-riff-1.0",
                    "gst-plugins-base::gstreamer-pbutils-1.0",
                    "gst-plugins-base::gstreamer-video-1.0",
                    "gst-plugins-base::gstreamer-audio-1.0",
                ]
            return []

        def openni2():
            return ["openni2::openni2"] if self.options.get_safe("with_openni2") else []

        def va():
            return ["libva::libva"] if self.options.get_safe("with_va") else []

        def gtk():
            return ["gtk::gtk"] if self.options.get_safe("with_gtk") else []

        def ipp():
            if self.options.with_ipp == "intel-ipp":
                return ["intel-ipp::intel-ipp"]
            elif self.options.with_ipp == "opencv-icv" and not self.options.shared:
                return ["ippiw"]
            return []

        def opencl():
            if self.options.get_safe("with_opencl") and not is_apple_os(self):
                return ["opencl-icd-loader::opencl-icd-loader"]
            return []

        def librealsense():
            return ["librealsense::librealsense"] if self.options.get_safe("with_librealsense") else []

        def parallel():
            if self.options.parallel == "openmp":
                return ["openmp::openmp"]
            if self.options.parallel == "tbb":
                return ["onetbb::libtbb"]
            return []

        def cudart():
            return ["cudart::cudart"] if self.options.with_cuda else []

        def cublas():
            return ["cublas::cublas_"] if self.options.get_safe("with_cublas") else []

        def cufft():
            return ["cufft::cufft"] if self.options.get_safe("with_cufft") else []

        def cudnn():
            return ["cudnn::cudnn"] if self.options.get_safe("dnn_cuda") else []

        def nvcodec():
            return []  # TODO

        def protobuf():
            return ["protobuf::protobuf"] if self.options.get_safe("with_protobuf") else []

        def qt():
            return ["qt::qt"] if self.options.get_safe("with_qt") else []

        def quirc():
            return ["quirc::quirc"] if self.options.get_safe("with_quirc") else []

        def tesseract():
            return ["tesseract::tesseract"] if self.options.get_safe("with_tesseract") else []

        def vulkan():
            return ["vulkan-headers::vulkan-headers"] if self.options.get_safe("with_vulkan") else []

        def wayland():
            return ["wayland::wayland-client", "wayland::wayland-cursor"] if self.options.get_safe("with_wayland") else []

        def xkbcommon():
            return ["xkbcommon::libxkbcommon"] if self.options.get_safe("with_wayland") else []

        def xvfb():
            return ["xorg-proto::xorg-proto"] if self.options.get_safe("with_framebuffer") else []

        def openvino():
            return ["openvino::Runtime"] if self.options.get_safe("with_openvino") else []

        def opencv_calib3d():
            return ["opencv_calib3d"] if self.options.calib3d else []

        def opencv_cudaarithm():
            return ["opencv_cudaarithm"] if self.options.cudaarithm else []

        def opencv_cudacodec():
            return ["opencv_cudacodec"] if self.options.cudacodec else []

        def opencv_cudafeatures2d():
            return ["opencv_cudafeatures2d"] if self.options.cudafeatures2d else []

        def opencv_cudafilters():
            return ["opencv_cudafilters"] if self.options.cudafilters else []

        def opencv_cudaimgproc():
            return ["opencv_cudaimgproc"] if self.options.cudaimgproc else []

        def opencv_cudalegacy():
            return ["opencv_cudalegacy"] if self.options.cudalegacy else []

        def opencv_cudaoptflow():
            return ["opencv_cudaoptflow"] if self.options.cudaoptflow else []

        def opencv_cudawarping():
            return ["opencv_cudawarping"] if self.options.cudawarping else []

        def opencv_dnn():
            return ["opencv_dnn"] if self.options.dnn else []

        def opencv_flann():
            return ["opencv_flann"] if self.options.flann else []

        def opencv_imgcodecs():
            return ["opencv_imgcodecs"] if self.options.imgcodecs else []

        def opencv_imgproc():
            return ["opencv_imgproc"] if self.options.imgproc else []

        def opencv_objdetect():
            return ["opencv_objdetect"] if self.options.objdetect else []

        def opencv_video():
            return ["opencv_video"] if self.options.video else []

        def opencv_videoio():
            return ["opencv_videoio"] if self.options.videoio else []

        def opencv_xfeatures2d():
            return ["opencv_xfeatures2d"] if self.options.xfeatures2d else []

        opencv_modules = {
            # Main modules
            "calib3d": {
                "is_built": self.options.calib3d,
                "mandatory_options": ["features2d", "flann", "imgproc"],
                "requires": ["opencv_core", "opencv_features2d", "opencv_flann", "opencv_imgproc"] +
                            eigen() + lapack() + ipp(),
            },
            "core": {
                "is_built": True,
                "no_option": True,
                "requires": ["zlib-ng::zlib-ng"] + parallel() + eigen() + ipp() + opencl() + va() + itt() + cudart(),
                "system_libs": [
                    (self.settings.os == "Android", ["dl", "m", "log"]),
                    (self.settings.os == "FreeBSD", ["m", "pthread"]),
                    (self.settings.os == "Linux", ["dl", "m", "pthread", "rt"]),
                ],
                "frameworks": [
                    (self.settings.os == "Macos" and self.options.get_safe("with_opencl"), ["OpenCL"]),
                ],
            },
            "dnn": {
                "is_built": self.options.dnn,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] +
                            cudnn() + cublas() + protobuf() + vulkan() + ipp() + openvino() + lapack(),
            },
            "features2d": {
                "is_built": self.options.features2d,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_imgproc"] + opencv_flann() + eigen() + ipp(),
            },
            "flann": {
                "is_built": self.options.flann,
                "requires": ["opencv_core"] + ipp(),
            },
            "gapi": {
                "is_built": self.options.gapi,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_imgproc", "ade::ade"] + openvino() + gstreamer() + va() + itt(),
                "system_libs": [
                    (self.settings.os == "Windows", ["ws2_32", "wsock32"]),
                ],
            },
            "highgui": {
                "is_built": self.options.highgui,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] + opencv_imgcodecs() +
                            opencv_videoio() + xvfb() + gtk() + qt() + xkbcommon() + wayland() + ipp(),
                "system_libs": [
                    (self.settings.os == "Windows", ["comctl32", "gdi32", "ole32", "setupapi", "ws2_32", "vfw32"]),
                ],
                "frameworks": [
                    (self.settings.os == "Macos", ["Cocoa"]),
                ],
            },
            "imgcodecs": {
                "is_built": self.options.imgcodecs,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_imgproc", "zlib-ng::zlib-ng"] + imageformats_deps() + ipp(),
                "frameworks": [
                    (is_apple_os(self), ["CoreFoundation", "CoreGraphics"]),
                    (self.settings.os == "iOS", ["UIKit"]),
                    (self.settings.os == "Macos", ["AppKit"]),
                ],
            },
            "imgproc": {
                "is_built": self.options.imgproc,
                "requires": ["opencv_core"] + ipp(),
            },
            "ml": {
                "is_built": self.options.ml,
                "requires": ["opencv_core"] + ipp(),
            },
            "objdetect": {
                "is_built": self.options.objdetect,
                "mandatory_options": ["calib3d", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc"] + quirc() + ipp(),
            },
            "photo": {
                "is_built": self.options.photo,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_imgproc"] + opencv_cudaarithm() + opencv_cudaimgproc() + ipp(),
            },
            "stitching": {
                "is_built": self.options.stitching,
                "mandatory_options": ["calib3d", "features2d", "flann", "imgproc"],
                "requires": ["opencv_calib3d", "opencv_features2d", "opencv_flann", "opencv_imgproc"] +
                            opencv_xfeatures2d() + opencv_cudaarithm() + opencv_cudawarping() +
                            opencv_cudafeatures2d() + opencv_cudalegacy() + opencv_cudaimgproc() + eigen() + ipp(),
            },
            "video": {
                "is_built": self.options.video,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_imgproc"] + opencv_calib3d() + ipp(),
            },
            "videoio": {
                "is_built": self.options.videoio,
                "mandatory_options": ["imgcodecs", "imgproc"],
                "requires": ["opencv_imgcodecs", "opencv_imgproc"] +
                            dc1394() + aravis() + ffmpeg() + gphoto2() + gstreamer() + librealsense() + openni2() + ipp(),
                "system_libs": [
                    (self.settings.os == "Android" and int(str(self.settings.os.api_level)) > 20, ["mediandk"]),
                ],
                "frameworks": [
                    (is_apple_os(self), ["Accelerate", "AVFoundation", "CoreGraphics", "CoreMedia", "CoreVideo", "QuartzCore"]),
                    (self.settings.os == "iOS", ["CoreImage", "UIKit"]),
                    (self.settings.os == "Macos", ["Cocoa"]),
                ],
            },
            # Extra modules
            "alphamat": {
                "is_built": self.options.get_safe("alphamat"),
                "mandatory_options": ["with_eigen", "imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
            },
            "aruco": {
                "is_built": self.options.aruco,
                "mandatory_options": ["calib3d", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc"] + ipp(),
            },
            "barcode": {
                "is_built": self.options.get_safe("barcode"),
                "mandatory_options": ["dnn", "imgproc"],
                "requires": ["opencv_core", "opencv_dnn", "opencv_imgproc"] + ipp(),
            },
            "bgsegm": {
                "is_built": self.options.bgsegm,
                "mandatory_options": ["calib3d", "imgproc", "video"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc", "opencv_video"] + ipp(),
            },
            "bioinspired": {
                "is_built": self.options.bioinspired,
                "requires": ["opencv_core"] + ipp(),
            },
            "ccalib": {
                "is_built": self.options.ccalib,
                "mandatory_options": ["calib3d", "features2d", "highgui", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_features2d", "opencv_highgui", "opencv_imgproc"] + ipp(),
            },
            "cudaarithm": {
                "is_built": self.options.cudaarithm,
                "mandatory_options": ["with_cuda"],
                "requires": ["opencv_core", "opencv_cudev", "npp::nppi"] + ipp() + cublas() + cufft(),
            },
            "cudabgsegm": {
                "is_built": self.options.cudabgsegm,
                "mandatory_options": ["with_cuda", "video"],
                "requires": ["opencv_video"] + ipp(),
            },
            "cudacodec": {
                "is_built": self.options.cudacodec,
                "mandatory_options": ["with_cuda", "videoio"],
                "requires": ["opencv_core", "opencv_videoio"] + ipp() + nvcodec(),
            },
            "cudafeatures2d": {
                "is_built": self.options.cudafeatures2d,
                "mandatory_options": ["with_cuda", "features2d", "cudafilters", "cudawarping"],
                "requires": ["opencv_features2d", "opencv_cudafilters", "opencv_cudawarping"] + ipp(),
            },
            "cudafilters": {
                "is_built": self.options.cudafilters,
                "mandatory_options": ["with_cuda", "imgproc", "cudaarithm"],
                "requires": ["opencv_imgproc", "opencv_cudaarithm", "npp::nppi"] + ipp(),
            },
            "cudaimgproc": {
                "is_built": self.options.cudaimgproc,
                "mandatory_options": ["with_cuda", "imgproc"],
                "requires": ["opencv_imgproc", "opencv_cudev", "npp::nppi"] + opencv_cudaarithm() + opencv_cudafilters() + ipp(),
            },
            "cudalegacy": {
                "is_built": self.options.cudalegacy,
                "mandatory_options": ["with_cuda", "video"],
                "requires": ["opencv_core", "opencv_video"] + opencv_calib3d() + opencv_imgproc() + opencv_objdetect() +
                            opencv_cudaarithm() + opencv_cudafilters() + opencv_cudaimgproc() + ipp(),
            },
            "cudaobjdetect": {
                "is_built": self.options.cudaobjdetect,
                "mandatory_options": ["with_cuda", "objdetect", "cudaarithm", "cudawarping"],
                "requires": ["opencv_objdetect", "opencv_cudaarithm", "opencv_cudawarping"] + opencv_cudalegacy() + ipp(),
            },
            "cudaoptflow": {
                "is_built": self.options.cudaoptflow,
                "mandatory_options": ["with_cuda", "video", "cudaarithm", "cudaimgproc", "cudawarping", "optflow"],
                "requires": ["opencv_video", "opencv_cudaarithm", "opencv_cudaimgproc", "opencv_cudawarping",
                             "opencv_optflow"] + opencv_cudalegacy() + ipp(),
            },
            "cudastereo": {
                "is_built": self.options.cudastereo,
                "mandatory_options": ["with_cuda", "calib3d"],
                "requires": ["opencv_calib3d", "opencv_cudev"] + ipp(),
            },
            "cudawarping": {
                "is_built": self.options.cudawarping,
                "mandatory_options": ["with_cuda", "imgproc"],
                "requires": ["opencv_core", "opencv_imgproc", "opencv_cudev", "npp::nppi"] + ipp(),
            },
            "cudev": {
                "is_built": self.options.with_cuda,
                "no_option": True,
                "requires": ipp(),
            },
            "cvv": {
                "is_built": self.options.cvv,
                "mandatory_options": ["with_qt", "features2d", "imgproc"],
                "requires": ["opencv_core", "opencv_features2d", "opencv_imgproc", "qt::qt"] + ipp(),
            },
            "datasets": {
                "is_built": self.options.datasets,
                "mandatory_options": ["flann", "imgcodecs", "ml"],
                "requires": ["opencv_core", "opencv_flann", "opencv_imgcodecs", "opencv_ml"] + ipp(),
            },
            "dnn_objdetect": {
                "is_built": self.options.dnn_objdetect,
                "mandatory_options": ["dnn", "imgproc"],
                "requires": ["opencv_core", "opencv_dnn", "opencv_imgproc"] + ipp(),
            },
            "dnn_superres": {
                "is_built": self.options.dnn_superres,
                "mandatory_options": ["dnn", "imgproc"],
                "requires": ["opencv_core", "opencv_dnn", "opencv_imgproc"] + ipp(),
            },
            "dpm": {
                "is_built": self.options.dpm,
                "mandatory_options": ["imgproc", "objdetect"],
                "requires": ["opencv_core", "opencv_imgproc", "opencv_objdetect"] + ipp(),
            },
            "face": {
                "is_built": self.options.face,
                "mandatory_options": ["calib3d", "imgproc", "objdetect", "photo"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc", "opencv_objdetect", "opencv_photo"] + ipp(),
            },
            "freetype": {
                "is_built": self.options.freetype,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc", "freetype::freetype", "harfbuzz::harfbuzz"] + ipp(),
            },
            "fuzzy": {
                "is_built": self.options.fuzzy,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
            },
            "hdf": {
                "is_built": self.options.hdf,
                "requires": ["opencv_core", "hdf5::hdf5"] + ipp(),
            },
            "hfs": {
                "is_built": self.options.hfs,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
            },
            "img_hash": {
                "is_built": self.options.img_hash,
                "is_part_of_world": False,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
            },
            "intensity_transform": {
                "is_built": self.options.get_safe("intensity_transform"),
                "requires": ["opencv_core"] + ipp(),
            },
            "line_descriptor": {
                "is_built": self.options.line_descriptor,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_imgproc"] + ipp(),
            },
            "mcc": {
                "is_built": self.options.get_safe("mcc"),
                "mandatory_options": ["calib3d", "dnn", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_dnn", "opencv_imgproc"] + ipp(),
            },
            "optflow": {
                "is_built": self.options.optflow,
                "mandatory_options": ["calib3d", "flann", "imgcodecs", "imgproc", "video", "ximgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_flann", "opencv_imgcodecs", "opencv_imgproc",
                             "opencv_video", "opencv_ximgproc"] + ipp(),
            },
            "ovis": {
                "is_built": self.options.ovis,
                "mandatory_options": ["calib3d", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc", "ogre::ogre"] + ipp(),
            },
            "phase_unwrapping": {
                "is_built": self.options.phase_unwrapping,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
            },
            "plot": {
                "is_built": self.options.plot,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
            },
            "quality": {
                "is_built": self.options.quality,
                "mandatory_options": ["imgproc", "ml"],
                "requires": ["opencv_core", "opencv_imgproc", "opencv_ml"] + ipp(),
            },
            "rapid": {
                "is_built": self.options.get_safe("rapid"),
                "mandatory_options": ["calib3d", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc"] + ipp(),
            },
            "reg": {
                "is_built": self.options.reg,
                "mandatory_options": ["imgproc"],
                "requires": ["opencv_core", "opencv_imgproc"] + ipp(),
            },
            "rgbd": {
                "is_built": self.options.rgbd,
                "mandatory_options": ["calib3d", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc"] + eigen() + ipp(),
            },
            "saliency": {
                "is_built": self.options.saliency,
                "mandatory_options": ["features2d", "imgproc"],
                "requires": ["opencv_features2d", "opencv_imgproc"] + ipp(),
            },
            "sfm": {
                "is_built": self.options.sfm,
                "is_part_of_world": False,
                "mandatory_options": ["with_eigen", "calib3d", "features2d", "imgcodecs", "xfeatures2d"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_features2d", "opencv_imgcodecs", "opencv_xfeatures2d",
                             "correspondence", "multiview", "numeric", "glog::glog", "gflags::gflags"] + eigen() + ipp(),
            },
            "shape": {
                "is_built": self.options.shape,
                "mandatory_options": ["calib3d", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc"] + ipp(),
            },
            "stereo": {
                "is_built": self.options.stereo,
                "mandatory_options": ["features2d", "imgproc", "tracking"],
                "requires": ["opencv_core", "opencv_features2d", "opencv_imgproc", "opencv_tracking"] + ipp(),
            },
            "structured_light": {
                "is_built": self.options.structured_light,
                "mandatory_options": ["calib3d", "imgproc", "phase_unwrapping"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgproc", "opencv_phase_unwrapping"] + ipp(),
            },
            "superres": {
                "is_built": self.options.get_safe("superres"),
                "mandatory_options": ["imgproc", "video", "optflow"],
                "requires": ["opencv_imgproc", "opencv_video", "opencv_optflow"] + opencv_videoio() + ipp() +
                            opencv_cudaarithm() + opencv_cudafilters() + opencv_cudawarping() + opencv_cudaimgproc() +
                            opencv_cudaoptflow() + opencv_cudacodec(),
            },
            "surface_matching": {
                "is_built": self.options.surface_matching,
                "mandatory_options": ["flann"],
                "requires": ["opencv_core", "opencv_flann"] + ipp(),
            },
            "text": {
                "is_built": self.options.text,
                "mandatory_options": ["dnn", "features2d", "imgproc", "ml"],
                "requires": ["opencv_core", "opencv_dnn", "opencv_features2d", "opencv_imgproc", "opencv_ml"] +
                            tesseract() + ipp(),
            },
            "tracking": {
                "is_built": self.options.tracking,
                "mandatory_options": ["imgproc", "video"],
                "requires": ["opencv_core", "opencv_imgproc", "opencv_video"] + opencv_dnn() + ipp(),
            },
            "videostab": {
                "is_built": self.options.videostab,
                "mandatory_options": ["calib3d", "features2d", "imgproc", "photo", "video"],
                "requires": ["opencv_calib3d", "opencv_features2d", "opencv_imgproc", "opencv_photo", "opencv_video"] +
                            opencv_videoio() + clp() + ipp() + opencv_cudawarping() + opencv_cudaoptflow(),
            },
            "viz": {
                "is_built": self.options.viz,
                "requires": ["opencv_core", "vtk::vtk"] + ipp(),
            },
            "wechat_qrcode": {
                "is_built": self.options.get_safe("wechat_qrcode"),
                "mandatory_options": ["dnn", "imgproc"],
                "requires": ["opencv_core", "opencv_dnn", "opencv_imgproc"] + ipp(),
            },
            "xfeatures2d": {
                "is_built": self.options.xfeatures2d,
                "mandatory_options": ["calib3d", "features2d", "imgproc"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_features2d", "opencv_imgproc"] + ipp() + opencv_cudaarithm(),
            },
            "ximgproc": {
                "is_built": self.options.ximgproc,
                "mandatory_options": ["calib3d", "imgcodecs", "imgproc", "video"],
                "requires": ["opencv_core", "opencv_calib3d", "opencv_imgcodecs", "opencv_imgproc", "opencv_video"] +
                            eigen() + ipp(),
            },
            "xobjdetect": {
                "is_built": self.options.xobjdetect,
                "mandatory_options": ["imgcodecs", "imgproc", "objdetect"],
                "requires": ["opencv_core", "opencv_imgcodecs", "opencv_imgproc", "opencv_objdetect"] + ipp(),
            },
            "xphoto": {
                "is_built": self.options.xphoto,
                "mandatory_options": ["imgproc", "photo"],
                "requires": ["opencv_core", "opencv_imgproc", "opencv_photo"] + ipp(),
            },
            # Extra targets (without prefix in their target & lib name)
            "ippiw": {
                "is_built": self.options.with_ipp == "opencv-icv" and not self.options.shared,
                "is_part_of_world": False,
                "no_option": True,
            },
            "numeric": {
                "is_built": self.options.sfm,
                "is_part_of_world": False,
                "no_option": True,
                "requires": eigen() + ipp(),
            },
            "correspondence": {
                "is_built": self.options.sfm,
                "is_part_of_world": False,
                "no_option": True,
                "requires": ["opencv_imgcodecs", "multiview", "glog::glog"] + eigen() + ipp(),
            },
            "multiview": {
                "is_built": self.options.sfm,
                "is_part_of_world": False,
                "no_option": True,
                "requires": ["numeric", "glog::glog"] + eigen() + ipp(),
            },
        }

        if Version(self.version) >= "4.3.0":
            opencv_modules["gapi"].setdefault("requires", []).extend(opencv_video())
        if Version(self.version) >= "4.5.2":
            opencv_modules["gapi"].setdefault("requires", []).extend(opencv_calib3d())
        if Version(self.version) >= "4.5.4":
            opencv_modules["objdetect"].setdefault("requires", []).extend(opencv_dnn())
        if Version(self.version) >= "4.5.1":
            opencv_modules["video"].setdefault("requires", []).extend(opencv_dnn())
        if Version(self.version) >= "4.4.0":
            opencv_modules["intensity_transform"].setdefault("mandatory_options", []).append("imgproc")
            opencv_modules["intensity_transform"].setdefault("requires", []).append("opencv_imgproc")
        if Version(self.version) < "4.3.0":
            opencv_modules["stereo"].setdefault("mandatory_options", []).extend(["calib3d", "video"])
            opencv_modules["stereo"].setdefault("requires", []).extend(["opencv_calib3d", "opencv_video"])
        if Version(self.version) >= "4.7.0":
            opencv_modules["aruco"].setdefault("mandatory_options", []).append("objdetect")
            opencv_modules["aruco"].setdefault("requires", []).append("opencv_objdetect")
            opencv_modules["cudacodec"].setdefault("mandatory_options", []).extend(["cudaarithm", "cudawarping"])
            opencv_modules["cudacodec"].setdefault("requires", []).extend(["opencv_cudaarithm", "opencv_cudawarping"])
            opencv_modules["wechat_qrcode"].setdefault("mandatory_options", []).append("objdetect")
            opencv_modules["wechat_qrcode"].setdefault("requires", []).append("opencv_objdetect")
        else:
            opencv_modules["cudacodec"].setdefault("requires", []).append("opencv_cudev")
        if Version(self.version) < "4.8.0":
            opencv_modules["dnn"].setdefault("mandatory_options", []).append("with_protobuf")

        return opencv_modules

    def _get_mandatory_disabled_options(self, opencv_modules):
        direct_options_to_enable = {}
        transitive_options_to_enable = {}

        # Check which direct options have to be enabled
        base_options = [option for option, values in opencv_modules.items()
                        if not values.get("no_option") and self.options.get_safe(option)]
        for base_option in base_options:
            for mandatory_option in opencv_modules.get(base_option, {}).get("mandatory_options", []):
                if not self.options.get_safe(mandatory_option):
                    direct_options_to_enable.setdefault(mandatory_option, set()).add(base_option)

        # Now traverse the graph to check which transitive options have to be enabled
        def collect_transitive_options(base_option, option):
            for mandatory_option in opencv_modules.get(option, {}).get("mandatory_options", []):
                if not self.options.get_safe(mandatory_option):
                    if mandatory_option not in transitive_options_to_enable:
                        transitive_options_to_enable[mandatory_option] = set()
                        collect_transitive_options(base_option, mandatory_option)
                    if base_option not in direct_options_to_enable.get(mandatory_option, set()):
                        transitive_options_to_enable[mandatory_option].add(base_option)

        for base_option in base_options:
            collect_transitive_options(base_option, base_option)

        return {
            "direct": direct_options_to_enable,
            "transitive": transitive_options_to_enable,
        }

    def _solve_internal_dependency_graph(self, opencv_modules):
        disabled_options = self._get_mandatory_disabled_options(opencv_modules)
        direct_options_to_enable = disabled_options["direct"]
        transitive_options_to_enable = disabled_options["transitive"]

        # Enable mandatory options
        all_options_to_enable = set(direct_options_to_enable.keys())
        all_options_to_enable.update(transitive_options_to_enable.keys())
        if all_options_to_enable:
            message = ("Several opencv options which were disabled will be enabled because "
                       "they are required by modules you have explicitly requested:\n")

            for option_to_enable in all_options_to_enable:
                try:
                    setattr(self.options, option_to_enable, True)
                except ConanException:
                    # It may not work in conan v2 and raise ConanException "Incorrect attempt to modify option"
                    continue

                direct_and_transitive = []
                direct = ", ".join(direct_options_to_enable.get(option_to_enable, []))
                if direct:
                    direct_and_transitive.append(f"direct dependency of {direct}")
                transitive = ", ".join(transitive_options_to_enable.get(option_to_enable, []))
                if transitive:
                    direct_and_transitive.append(f"transitive dependency of {transitive}")
                message += f"  - {option_to_enable}: {' / '.join(direct_and_transitive)}\n"

            self.output.warning(message)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

        # Call this first before any further manipulation of options based on other options
        self._solve_internal_dependency_graph(self._opencv_modules)

        if not (self._has_openvino_option and (self.options.gapi or self.options.dnn)):
            self.options.rm_safe("with_openvino")

        if not self.options.calib3d and not self.options.dnn:
            self.options.rm_safe("with_lapack")
        if not self.options.dnn:
            self.options.rm_safe("dnn_cuda")
            self.options.rm_safe("with_flatbuffers")
            self.options.rm_safe("with_protobuf")
            self.options.rm_safe("with_vulkan")
        if not self.options.highgui:
            self.options.rm_safe("with_gtk")
            self.options.rm_safe("with_wayland")
        if not (self.options.highgui or self.options.cvv):
            self.options.rm_safe("with_qt")
        if not self.options.imgcodecs:
            self.options.rm_safe("with_avif")
            self.options.rm_safe("with_jpeg")
            self.options.rm_safe("with_jpegxl")
            self.options.rm_safe("with_jpeg2000")
            self.options.rm_safe("with_openexr")
            self.options.rm_safe("with_png")
            self.options.rm_safe("with_tiff")
            self.options.rm_safe("with_webp")
            self.options.rm_safe("with_gdal")
            self.options.rm_safe("with_gdcm")
            self.options.rm_safe("with_imgcodec_hdr")
            self.options.rm_safe("with_imgcodec_pfm")
            self.options.rm_safe("with_imgcodec_pxm")
            self.options.rm_safe("with_imgcodec_sunraster")
            self.options.rm_safe("with_msmf")
            self.options.rm_safe("with_msmf_dxva")
        if not self.options.objdetect:
            self.options.rm_safe("with_quirc")
        if not self.options.videoio:
            self.options.rm_safe("with_1394")
            self.options.rm_safe("with_aravis")
            self.options.rm_safe("with_ffmpeg")
            self.options.rm_safe("with_gphoto2")
            self.options.rm_safe("with_librealsense")
            self.options.rm_safe("with_openni2")
            self.options.rm_safe("with_v4l")
            self.options.rm_safe("with_va")
        if not self.options.videoio and not self.options.gapi:
            self.options.rm_safe("with_gstreamer")
        if not self.options.with_cuda:
            del self.settings.cuda
            self.options.rm_safe("with_cublas")
            self.options.rm_safe("with_cufft")
            self.options.rm_safe("dnn_cuda")
        if not self.options.text:
            self.options.rm_safe("with_tesseract")
        if not self.options.videostab:
            self.options.rm_safe("with_clp")

        if self.options.build_all_base:
            self.options.update(
                options={module: [True, False] for module in OPENCV_MAIN_MODULES_OPTIONS},
                options_values={module: True for module in OPENCV_MAIN_MODULES_OPTIONS},
            )
        if self.options.build_all_contrib:
            self.options.update(
                options={module: [True, False] for module in OPENCV_EXTRA_MODULES_OPTIONS},
                options_values={module: True for module in OPENCV_EXTRA_MODULES_OPTIONS},
            )

    def package_id(self):
        del self.info.options.build_all_base
        del self.info.options.build_all_contrib

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # core module dependencies
        self.requires("zlib-ng/[^2.0]")
        if self.options.with_eigen:
            self.requires("eigen/[>=3.3 <6]")
        if self.options.get_safe("with_lapack"):
            self.requires("lapack/latest")
        if self.options.get_safe("with_clp"):
            self.requires("coin-clp/[^1.17.6]")
        if self.options.with_cuda:
            # Used in opencv2/cudev/ public headers
            self.cuda.requires("cudart", transitive_headers=True)
            if self.options.with_cublas:
                self.cuda.requires("cublas")
            if self.options.with_cufft:
                self.cuda.requires("cufft")
            if self.options.get_safe("dnn_cuda"):
                self.requires("cudnn/[>=8 <10]")
            if any(self.options.get_safe(mod) for mod in ["cudaarithm", "cudaimgproc", "cudafilters", "cudawarping"]):
                self.cuda.requires("npp")
        if self.options.parallel == "openmp":
            self.requires("openmp/system")
        elif self.options.parallel == "tbb":
            self.requires("onetbb/[>=2021 <2023]")
        if self.options.with_ipp == "intel-ipp":
            self.requires("intel-ipp/2020")
        if self.options.get_safe("with_opencl") and not is_apple_os(self):
            self.requires("opencl-icd-loader/[*]")
        if self.options.with_itt:
            self.requires("ittapi/[^3.25.5]")
        # dnn module dependencies
        if self.options.get_safe("with_protobuf"):
            # Symbols are exposed https://github.com/conan-io/conan-center-index/pull/16678#issuecomment-1507811867
            if Version(self.version) >= "4.11.0":
                self.requires("protobuf/[>=3.21.12]", transitive_libs=True)
            else:
                self.requires("protobuf/[>=3.21.12 <6]", transitive_libs=True)
        if self.options.get_safe("with_vulkan"):
            self.requires("vulkan-headers/[^1.3.239.0]")
        if self.options.get_safe("with_openvino"):
            self.requires("openvino/[>=2024.5.0]")
        # gapi module dependencies
        if self.options.gapi:
            self.requires("ade/0.1.2d")
        # highgui module dependencies
        if self.options.get_safe("with_framebuffer"):
            self.requires("xorg-proto/2024.1")
        if self.options.get_safe("with_gtk"):
            self.requires("gtk/[~3.24]")
        if self.options.get_safe("with_qt"):
            self.requires("qt/[>=5.15 <7]")
        if self.options.get_safe("with_wayland"):
            self.requires("wayland/[^1.22.0]")
            self.requires("xkbcommon/[^1.6.0]")
        # imgcodecs module dependencies
        if self.options.get_safe("with_avif"):
            self.requires("libavif/[^1.0.4]")
        if self.options.get_safe("with_jpeg"):
            self.requires("libjpeg-meta/latest")
        if self.options.get_safe("with_jpegxl"):
            self.requires("libjxl/0.11.1")
        if self.options.get_safe("with_jpeg2000") == "openjpeg":
            self.requires("openjpeg/[^2.5.2]")
        elif self.options.get_safe("with_jpeg2000") == "jasper":
            self.requires("jasper/[^4.2]")
        if self.options.get_safe("with_png"):
            self.requires("libpng/[~1.6]")
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
        # objdetect module dependencies
        if self.options.get_safe("with_quirc"):
            self.requires("quirc/1.2")
        # videoio module dependencies
        if self.options.get_safe("with_ffmpeg"):
            if Version(self.version) >= "4.12":
                self.requires("ffmpeg/[*]")
            else:
                self.requires("ffmpeg/[<8]")
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
        # freetype module dependencies
        if self.options.freetype:
            self.requires("freetype/[^2.13.2]")
            self.requires("harfbuzz/[*]")
        # hdf module dependencies
        if self.options.hdf:
            self.requires("hdf5/[^1.8]")
        # ovis module dependencies
        if self.options.ovis:
            self.requires("ogre/[>=14.3]")
        # sfm module dependencies
        if self.options.sfm:
            self.requires("gflags/2.2.2")
            self.requires("glog/[>=0.6 <1]")
        # text module dependencies
        if self.options.get_safe("with_tesseract"):
            self.requires("tesseract/[^5.3.3]")

    def _check_mandatory_options(self, opencv_modules):
        disabled_options = self._get_mandatory_disabled_options(opencv_modules)
        direct_disabled_mandatory_options = disabled_options["direct"]
        transitive_disabled_mandatory_options = disabled_options["transitive"]

        # check mandatory options
        all_disabled_mandatory_options = set(direct_disabled_mandatory_options.keys())
        all_disabled_mandatory_options.update(transitive_disabled_mandatory_options.keys())
        if all_disabled_mandatory_options:
            message = ("Several opencv options are disabled but are required by modules "
                       "you have explicitly requested:\n")

            for disabled_option in all_disabled_mandatory_options:
                direct_and_transitive = []
                direct = ", ".join(direct_disabled_mandatory_options.get(disabled_option, []))
                if direct:
                    direct_and_transitive.append(f"direct dependency of {direct}")
                transitive = ", ".join(transitive_disabled_mandatory_options.get(disabled_option, []))
                if transitive:
                    direct_and_transitive.append(f"transitive dependency of {transitive}")
                message += f"  - {disabled_option}: {' / '.join(direct_and_transitive)}\n"

            raise ConanInvalidConfiguration(message)

    def validate(self):
        self._check_mandatory_options(self._opencv_modules)
        check_min_cppstd(self, 11)
        if self.options.shared and self._is_cl_like and self._is_cl_like_static_runtime:
            raise ConanInvalidConfiguration("MSVC or clang-cl with static runtime are not supported for shared library.")
        if self.settings.compiler == "clang" and Version(self.settings.compiler.version) < "4":
            raise ConanInvalidConfiguration("Clang 3.x can't build OpenCV 4.x due to an internal bug.")
        if self.options.get_safe("dnn_cuda") and \
            (not self.options.with_cuda or not self.options.with_cublas):
            raise ConanInvalidConfiguration("with_cublas and with_cudnn must be enabled for dnn_cuda")
        if self.options.with_ipp == "opencv-icv" and \
           not (self.settings.arch in ["x86", "x86_64"] and self.settings.os in ["Linux", "Macos", "Windows"]):
            raise ConanInvalidConfiguration(f"opencv-icv is not available for {self.settings.os}/{self.settings.arch}")
        if self.options.viz:
            raise ConanInvalidConfiguration(
                "viz module can't be enabled yet. It requires VTK which is not available in conan-center."
            )
        if self.options.get_safe("with_jpeg2000") == "openjpeg" and Version(self.version) < "4.3.0":
            raise ConanInvalidConfiguration("openjpeg is not available for OpenCV before 4.3.0")
        if self.options.with_cuda:
            self.cuda.validate_settings()
            if Version(self.version) <= "4.12.0" and self.cuda.major >= 13:
                raise ConanInvalidConfiguration(f"{self.ref} does not support CUDA 13+")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.27 <5]")
        if self.options.get_safe("with_protobuf"):
            self.tool_requires("protobuf/<host_version>")
        if self.options.get_safe("with_wayland"):
            self.tool_requires("wayland/<host_version>")
        if self._build_depends_on_pkgconfig and not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.get_safe("with_qt"):
            self.tool_requires("qt/<host_version>")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version][0], strip_root=True)
        get(self, **self.conan_data["sources"][self.version][1], destination=self._contrib_folder, strip_root=True)
        apply_conandata_patches(self)

        # Don't force only Release or Debug as build_type
        replace_in_file(self, "CMakeLists.txt",
                        "ocv_update(CMAKE_CONFIGURATION_TYPES",
                        "# ocv_update(CMAKE_CONFIGURATION_TYPES")

        ## Remove 3rd party libs
        for directory in [
            "include", "libjasper", "libjpeg", "libjpeg-turbo", "libpng", "libspng", "libtiff",
            "libwebp", "openexr", "openjpeg", "protobuf", "quirc", "tbb", "zlib", "zlib-ng",
        ]:
            rmdir(self, os.path.join("3rdparty", directory))
        replace_in_file(self, "cmake/OpenCVDetectOpenCL.cmake", "ocv_install_3rdparty_licenses", "# ocv_install_3rdparty_licenses")
        replace_in_file(self, "CMakeLists.txt", "add_subdirectory(3rdparty/quirc)", "")

        replace_in_file(self, "CMakeLists.txt", "ANDROID OR NOT UNIX", "FALSE")
        replace_in_file(self, "CMakeLists.txt", "elseif(EMSCRIPTEN)", "elseif(QNXNTO)\nelseif(EMSCRIPTEN)")

        ## Fix link to several dependencies
        replace_in_file(self, "modules/imgcodecs/CMakeLists.txt", "JASPER_", "Jasper_")
        replace_in_file(self, "modules/imgcodecs/CMakeLists.txt", "${GDAL_LIBRARY}", "GDAL::GDAL")
        if Version(self.version) >= "4.8.0":
            replace_in_file(self, "modules/imgcodecs/CMakeLists.txt", "${AVIF_LIBRARY}", "avif")
        replace_in_file(self, "modules/videoio/cmake/detect_realsense.cmake",
                        'ocv_add_external_target(librealsense "" "${realsense2_LIBRARY}" "HAVE_LIBREALSENSE")',
                        'ocv_add_external_target(librealsense "${realsense2_INCLUDE_DIRS}" "${realsense2_LIBRARIES}" "HAVE_LIBREALSENSE")')

        ## Fix detection of ffmpeg
        replace_in_file(self, "modules/videoio/cmake/detect_ffmpeg.cmake", "FFMPEG_FOUND", "ffmpeg_FOUND")

        # Find libva from Conan
        save(self, "cmake/OpenCVFindVA.cmake", "find_package(libva ${VA_REQUIRED})\n")

        save(self, "cmake/OpenCVFindWebP.cmake",
             "find_package(WebP CONFIG)\n"
             "set(WEBP_FOUND ${WebP_FOUND})\n")

        save(self, "modules/videoio/cmake/detect_openni2.cmake",
             "find_package(OPENNI2 ${OPENNI2_REQUIRED})\n"
             "set(HAVE_OPENNI2 ${OPENNI2_FOUND})\n"
             'ocv_add_external_target(openni2 "${OPENNI2_INCLUDE_DIRS}" "${OPENNI2_LIBRARIES}" "HAVE_OPENNI2")\n')

        # Use pkg-config to find Clp even on Windows
        replace_in_file(self, "cmake/OpenCVFindLibsPerf.cmake", "if(UNIX)", "if(TRUE)")
        # Fix a CMake bug
        replace_in_file(self, "cmake/OpenCVFindLibsPerf.cmake",
                        'if(NOT ${CLP_INCLUDE_DIRS} STREQUAL "")',
                        'if(NOT CLP_INCLUDE_DIRS STREQUAL "")')

        # Add support for external ITT
        save(self, "cmake/OpenCVDetectTrace.cmake",
             "if(WITH_ITT)\n"
             "  find_package(ITT REQUIRED)\n"
             "  set(HAVE_ITT 1)\n"
             "endif()\n"
             "set(OPENCV_TRACE 1)")

        if Version(self.version) >= "4.11.0":
            save(self, "cmake/OpenCVFindJPEGXL.cmake", "find_package(JPEGXL REQUIRED)\n")

        ## Cleanup RPATH
        replace_in_file(self, "cmake/OpenCVInstallLayout.cmake", 'ocv_update(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/${OPENCV_LIB_INSTALL_PATH}")', "")
        replace_in_file(self, "cmake/OpenCVInstallLayout.cmake", "set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)", "")

        # Respect cppstd from Conan
        if Version(self.version) < "4.12":
            replace_in_file(self, "cmake/OpenCVDetectCXXCompiler.cmake", 'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")', "")
        for path, min_ver in [
            ("cmake/OpenCVPluginStandalone.cmake", "4.5.2"),
            ("modules/dnn/cmake/plugin.cmake", "4.7.0"),
            ("modules/gapi/cmake/standalone.cmake", "4.1"),
            ("modules/highgui/cmake/plugin.cmake", "4.5.3"),
            ("modules/objc/generator/templates/cmakelists.template", "4.4.0"),
            ("modules/videoio/cmake/plugin.cmake", "4.1"),
            ("modules/videoio/cmake/plugin_standalone.cmake", "4.1"),
        ]:
            if Version(self.version) >= min_ver and os.path.exists(path):
                replace_in_file(self, path, "CXX_STANDARD 11", "")

        # Fix propagation of CUDA deps
        save(self, "modules/core/CMakeLists.txt",
             "\nif(HAVE_CUDA)\n"
             "  target_link_libraries(${the_module} PUBLIC CUDA::toolkit)\n"
             "endif()\n",
             append=True)
        # Let CudaToolchain manage CUDA architecture flags
        if Version(self.version) >= "4.9.0":
            replace_in_file(self, "cmake/OpenCVDetectCUDA.cmake",
                            "ocv_set_cuda_arch_bin_and_ptx(",
                            "# ocv_set_cuda_arch_bin_and_ptx(")
            replace_in_file(self, "cmake/OpenCVDetectCUDALanguage.cmake",
                            "ocv_set_cuda_arch_bin_and_ptx(",
                            "# ocv_set_cuda_arch_bin_and_ptx(")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["OPENCV_CONFIG_INSTALL_PATH"] = "cmake"
        tc.variables["OPENCV_BIN_INSTALL_PATH"] = "bin"
        tc.variables["OPENCV_LIB_INSTALL_PATH"] = "lib"
        tc.variables["OPENCV_3P_LIB_INSTALL_PATH"] = "lib"
        tc.variables["OPENCV_LICENSES_INSTALL_PATH"] = "licenses"

        tc.variables["OPENCV_SKIP_CMAKE_CXX_STANDARD"] = True

        tc.variables["BUILD_CUDA_STUBS"] = False
        tc.variables["BUILD_DOCS"] = False
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_FAT_JAVA_LIB"] = False
        tc.variables["BUILD_IPP_IW"] = self.options.with_ipp == "opencv-icv"
        tc.variables["BUILD_ITT"] = False
        tc.variables["BUILD_JASPER"] = False
        tc.variables["BUILD_JAVA"] = False
        tc.variables["BUILD_JPEG"] = False
        tc.variables["BUILD_OPENEXR"] = False
        tc.variables["BUILD_OPENJPEG"] = False
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_PROTOBUF"] = False
        tc.variables["BUILD_PACKAGE"] = False
        tc.variables["BUILD_PERF_TESTS"] = False
        tc.variables["BUILD_USE_SYMLINKS"] = False
        tc.variables["BUILD_opencv_apps"] = False
        tc.variables["BUILD_opencv_java"] = False
        tc.variables["BUILD_opencv_java_bindings_gen"] = False
        tc.variables["BUILD_opencv_js"] = False
        tc.variables["BUILD_ZLIB"] = False
        tc.variables["BUILD_PNG"] = False
        tc.variables["BUILD_TIFF"] = False
        tc.variables["BUILD_WEBP"] = False
        tc.variables["BUILD_TBB"] = False
        tc.variables["OPENCV_FORCE_3RDPARTY_BUILD"] = False
        tc.variables["OPENCV_PYTHON_SKIP_DETECTION"] = True
        tc.variables["BUILD_opencv_python2"] = False
        tc.variables["BUILD_opencv_python3"] = False
        tc.variables["BUILD_opencv_python_bindings_g"] = False
        tc.variables["BUILD_opencv_python_tests"] = False
        tc.variables["BUILD_opencv_ts"] = False

        tc.variables["WITH_1394"] = self.options.get_safe("with_1394", False)
        tc.variables["WITH_ARAVIS"] = self.options.get_safe("with_aravis", False)
        tc.variables["WITH_CLP"] = self.options.get_safe("with_clp", False)
        tc.variables["WITH_NVCUVID"] = False

        tc.variables["WITH_FFMPEG"] = self.options.get_safe("with_ffmpeg", False)
        if self.options.get_safe("with_ffmpeg"):
            tc.variables["OPENCV_FFMPEG_SKIP_BUILD_CHECK"] = True
            tc.variables["OPENCV_FFMPEG_SKIP_DOWNLOAD"] = True
            # opencv will not search for ffmpeg package, but for
            # libavcodec;libavformat;libavutil;libswscale modules
            tc.variables["OPENCV_FFMPEG_USE_FIND_PACKAGE"] = "ffmpeg"
            tc.variables["OPENCV_INSTALL_FFMPEG_DOWNLOAD_SCRIPT"] = False
            if Version(self.version) >= "4.7.0":
                tc.variables["OPENCV_FFMPEG_ENABLE_LIBAVDEVICE"] = False
            ffmpeg_libraries = []
            for component in ["avcodec",  "avformat", "avutil", "swscale", "avresample"]:
                if component == "avutil" or self.dependencies["ffmpeg"].options.get_safe(component):
                    ffmpeg_libraries.append(f"ffmpeg::{component}")
                    ffmpeg_component_version = self.dependencies["ffmpeg"].cpp_info.components[component].get_property("component_version")
                    tc.variables[f"FFMPEG_lib{component}_VERSION"] = ffmpeg_component_version
            tc.variables["FFMPEG_LIBRARIES"] = ";".join(ffmpeg_libraries)

        tc.variables["WITH_GSTREAMER"] = self.options.get_safe("with_gstreamer", False)
        tc.variables["OPENCV_GAPI_GSTREAMER"] = self.options.get_safe("with_gstreamer", False)
        tc.variables["WITH_HALIDE"] = False
        tc.variables["WITH_HPX"] = False
        tc.variables["WITH_IMGCODEC_HDR"] = self.options.get_safe("with_imgcodec_hdr", False)
        tc.variables["WITH_IMGCODEC_PFM"] = self.options.get_safe("with_imgcodec_pfm", False)
        tc.variables["WITH_IMGCODEC_PXM"] = self.options.get_safe("with_imgcodec_pxm", False)
        tc.variables["WITH_IMGCODEC_SUNRASTER"] = self.options.get_safe("with_imgcodec_sunraster", False)
        tc.variables["WITH_IPP"] = bool(self.options.with_ipp)
        if self.options.with_ipp == "intel-ipp":
            ipp_root = self.dependencies["intel-ipp"].package_folder.replace("\\", "/")
            tc.variables["IPPROOT"] = ipp_root
            tc.variables["IPPIWROOT"] = ipp_root
        tc.variables["WITH_ITT"] = self.options.with_itt
        tc.variables["WITH_LIBREALSENSE"] = self.options.get_safe("with_librealsense", False)
        tc.variables["WITH_MFX"] = False
        tc.variables["WITH_OPENCL"] = self.options.get_safe("with_opencl", False)
        tc.variables["WITH_OPENCLAMDBLAS"] = False
        tc.variables["WITH_OPENCLAMDFFT"] = False
        tc.variables["WITH_OPENCL_SVM"] = False
        tc.variables["WITH_OPENGL"] = False
        tc.variables["WITH_TBB"] = self.options.parallel == "tbb"
        tc.variables["WITH_OPENMP"] = self.options.parallel == "openmp"
        tc.variables["WITH_OPENNI"] = False
        tc.variables["WITH_OPENNI2"] = self.options.get_safe("with_openni2", False)
        tc.variables["WITH_OPENVX"] = False
        tc.variables["WITH_CAROTENE"] = False
        tc.variables["WITH_PLAIDML"] = False
        tc.variables["WITH_PVAPI"] = False
        tc.variables["WITH_QT"] = self.options.get_safe("with_qt", False)
        tc.variables["WITH_QUIRC"] = self.options.get_safe("with_quirc", False)
        tc.variables["WITH_V4L"] = self.options.get_safe("with_v4l", False)
        tc.variables["WITH_VA"] = self.options.get_safe("with_va", False)
        tc.variables["WITH_VA_INTEL"] = self.options.get_safe("with_va", False) and self.options.get_safe("with_opencl", False)
        tc.variables["WITH_VTK"] = self.options.viz
        tc.variables["WITH_VULKAN"] = self.options.get_safe("with_vulkan", False)
        if self.options.get_safe("with_vulkan"):
            tc.variables["VULKAN_INCLUDE_DIRS"] = os.path.join(self.dependencies["vulkan-headers"].package_folder, "include").replace("\\", "/")
        tc.variables["WITH_XIMEA"] = False
        tc.variables["WITH_XINE"] = False
        tc.variables["WITH_LAPACK"] = self.options.get_safe("with_lapack", False)

        tc.variables["WITH_FRAMEBUFFER"] = self.options.get_safe("with_framebuffer", False)
        tc.variables["WITH_FRAMEBUFFER_XVFB"] = self.options.get_safe("with_framebuffer", False)
        tc.variables["WITH_GTK"] = self.options.get_safe("with_gtk", False)
        tc.variables["WITH_GTK_2_X"] = self._is_gtk_version2
        tc.variables["WITH_WEBP"] = self.options.get_safe("with_webp", False)
        tc.variables["WITH_JPEG"] = bool(self.options.get_safe("with_jpeg", False))
        tc.variables["WITH_JPEGXL"] = self.options.get_safe("with_jpegxl", False)
        tc.variables["WITH_PNG"] = self.options.get_safe("with_png", False)
        if self._has_with_tiff_option:
            tc.variables["WITH_TIFF"] = self.options.get_safe("with_tiff", False)
        if self._has_with_jpeg2000_option:
            tc.variables["WITH_JASPER"] = self.options.get_safe("with_jpeg2000") == "jasper"
            tc.variables["WITH_OPENJPEG"] = self.options.get_safe("with_jpeg2000") == "openjpeg"
        tc.variables["WITH_OPENEXR"] = self.options.get_safe("with_openexr", False)
        tc.variables["WITH_GDAL"] = self.options.get_safe("with_gdal", False)
        tc.variables["WITH_GPHOTO2"] = self.options.get_safe("with_gphoto2", False)
        tc.variables["WITH_GDCM"] = self.options.get_safe("with_gdcm", False)
        tc.variables["WITH_EIGEN"] = self.options.with_eigen
        tc.variables["WITH_DSHOW"] = self._is_cl_like
        tc.variables["WITH_MSMF"] = self.options.get_safe("with_msmf", False)
        tc.variables["WITH_MSMF_DXVA"] = self.options.get_safe("with_msmf_dxva", False)
        tc.variables["OPENCV_MODULES_PUBLIC"] = "opencv"
        tc.variables["OPENCV_ENABLE_NONFREE"] = self.options.nonfree

        if self.options.cpu_baseline or self.options.cpu_baseline == "":
            tc.variables["CPU_BASELINE"] = self.options.cpu_baseline

        if self.options.cpu_dispatch or self.options.cpu_dispatch == "":
            tc.variables["CPU_DISPATCH"] = self.options.cpu_dispatch

        tc.variables["OPENCV_DNN_CUDA"] = self.options.get_safe("dnn_cuda", False)

        if Version(self.version) >= "4.6.0":
            tc.variables["WITH_OPENVINO"] = self.options.get_safe("with_openvino", False)
            tc.variables["WITH_TIMVX"] = False
        else:
            tc.variables["WITH_INF_ENGINE"] = False
            tc.variables["WITH_NGRAPH"] = False

        if Version(self.version) >= "4.7.0":
            tc.variables["ENABLE_DELAYLOAD"] = False
            tc.variables["WITH_CANN"] = False
            tc.variables["WITH_SPNG"] = False # TODO: change with_png recipe option in order to use either libpng or libspng
            tc.variables["WITH_WAYLAND"] = self.options.get_safe("with_wayland", False)

        if Version(self.version) >= "4.8.0":
            tc.variables["WITH_AVIF"] = self.options.get_safe("with_avif", False)
            tc.variables["WITH_FLATBUFFERS"] = self.options.get_safe("with_flatbuffers", False)

        if Version(self.version) >= "4.10.0":
            tc.variables["WITH_KLEIDICV"] = False
            tc.variables["WITH_NDSRVP"] = False
            tc.variables["OBSENSOR_USE_ORBBEC_SDK"] = False
            if is_apple_os(self):
                # default behavior for 4.9.0
                tc.variables["WITH_OBSENSOR"] = False
            tc.variables["WITH_ZLIB_NG"] = False

        if Version(self.version) >= "4.11.0":
            tc.variables["WITH_HAL_RVV"] = False
        else:
            tc.variables["ENABLE_NEON"] = self.options.get_safe("neon", False)

        # Special world option merging all enabled modules into one big library file
        tc.variables["BUILD_opencv_world"] = self.options.world

        # Main modules
        tc.variables["BUILD_opencv_core"] = True
        for module in OPENCV_MAIN_MODULES_OPTIONS:
            tc.variables[f"BUILD_opencv_{module}"] = self.options.get_safe(module, False)
        tc.variables["WITH_PROTOBUF"] = self.options.get_safe("with_protobuf", False)
        if self.options.get_safe("with_protobuf"):
            tc.variables["PROTOBUF_UPDATE_FILES"] = True
        tc.variables["WITH_ADE"] = self.options.gapi

        # Extra modules
        if any(self.options.get_safe(module) for module in OPENCV_EXTRA_MODULES_OPTIONS) or self.options.with_cuda:
            tc.variables["OPENCV_EXTRA_MODULES_PATH"] = self._extra_modules_folder.replace("\\", "/")
        tc.variables["BUILD_opencv_cudev"] = self.options.with_cuda
        for module in OPENCV_EXTRA_MODULES_OPTIONS:
            tc.variables[f"BUILD_opencv_{module}"] = self.options.get_safe(module, False)
        tc.variables["BUILD_opencv_cnn_3dobj"] = False
        if Version(self.version) >= "4.4.0":
            tc.variables["BUILD_opencv_julia"] = False
        tc.variables["BUILD_opencv_matlab"] = False
        if self.options.text:
            tc.variables["WITH_TESSERACT"] = self.options.with_tesseract

        if self.options.get_safe("with_openni"):
            tc.variables["OPENNI2_REQUIRED"] = "REQUIRED"

        if self.options.get_safe("with_va"):
            tc.variables["VA_INCLUDE_DIR"] = self.dependencies["libva"].cpp_info.includedir.replace("\\", "/")
            tc.variables["VA_LIBRARIES"] = "libva::libva"
            tc.variables["VA_REQUIRED"] = "REQUIRED"

        if self.options.get_safe("with_jpeg2000") == "openjpeg":
            openjpeg_version = Version(self.dependencies["openjpeg"].ref.version)
            tc.variables["OPENJPEG_MAJOR_VERSION"] = openjpeg_version.major
            tc.variables["OPENJPEG_MINOR_VERSION"] = openjpeg_version.minor
            tc.variables["OPENJPEG_BUILD_VERSION"] = openjpeg_version.patch

        if self.options.get_safe("with_opencl") and not is_apple_os(self):
            tc.variables["OPENCL_INCLUDE_DIR"] = self.dependencies["opencl-headers"].cpp_info.includedir.replace("\\", "/")
            opencl_libdir = self.dependencies["opencl-icd-loader"].cpp_info.libdir
            opencl_lib = sorted(Path(opencl_libdir).iterdir())[0]
            tc.variables["OPENCL_LIBRARY"] = str(opencl_lib).replace("\\", "/")

        tc.variables["WITH_CUDA"] = self.options.with_cuda
        tc.variables["WITH_CUBLAS"] = self.options.get_safe("with_cublas", False)
        tc.variables["WITH_CUFFT"] = self.options.get_safe("with_cufft", False)
        tc.variables["WITH_CUDNN"] = self.options.get_safe("dnn_cuda", False)
        tc.variables["ENABLE_CUDA_FIRST_CLASS_LANGUAGE"] = True
        # This allows compilation on older GCC/NVCC, otherwise build errors.
        tc.variables["CUDA_NVCC_FLAGS"] = "--expt-relaxed-constexpr"

        tc.variables["ENABLE_PIC"] = self.options.get_safe("fPIC", True)
        tc.variables["ENABLE_CCACHE"] = False

        if self._is_cl_like:
            tc.variables["BUILD_WITH_STATIC_CRT"] = self._is_cl_like_static_runtime

        if self.settings.os == "Android":
            tc.variables["BUILD_ANDROID_EXAMPLES"] = False

        tc.variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)

        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("ittapi", "cmake_file_name", "ITT")
        deps.set_property("libjxl", "cmake_file_name", "JPEGXL")
        deps.set_property("openni2", "cmake_file_name", "OPENNI2")
        deps.generate()

        if self._build_depends_on_pkgconfig:
            deps = PkgConfigDeps(self)
            deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def _patch_sources(self):
        ## Robust handling of wayland
        if self.options.get_safe("with_wayland"):
            detect_wayland = os.path.join(self.source_folder, "modules", "highgui", "cmake", "detect_wayland.cmake")
            # We have to override *_LINK_LIBRARIES variables linked to highui because they are just link fkags, not cflags
            # so include dirs are missing (OpenCV seems to assume system libs for wayland)
            replace_in_file(self, detect_wayland,
                            "ocv_check_modules(WAYLAND_CLIENT wayland-client)",
                            "ocv_check_modules(WAYLAND_CLIENT wayland-client)\n"
                            "find_package(wayland REQUIRED CONFIG)\n"
                            "set(WAYLAND_CLIENT_LINK_LIBRARIES wayland::wayland-client)")
            replace_in_file(self, detect_wayland,
                            "ocv_check_modules(WAYLAND_CURSOR wayland-cursor)",
                            "ocv_check_modules(WAYLAND_CURSOR wayland-cursor)\n"
                            "set(WAYLAND_CURSOR_LINK_LIBRARIES wayland::wayland-cursor)")
            replace_in_file(self, detect_wayland,
                            "ocv_check_modules(XKBCOMMON xkbcommon)",
                            "ocv_check_modules(XKBCOMMON xkbcommon)\n"
                            "find_package(xkbcommon REQUIRED CONFIG)\n"
                            "set(XKBCOMMON_LINK_LIBRARIES xkbcommon::libxkbcommon)")

        ## Fix discovery & link of protobuf
        if self.options.get_safe("with_protobuf"):
            find_protobuf = os.path.join(self.source_folder, "cmake", "OpenCVFindProtobuf.cmake")
            # OpenCV expects to find FindProtobuf.cmake, not the config file
            replace_in_file(self, find_protobuf,
                            "find_package(Protobuf QUIET)",
                            "find_package(Protobuf REQUIRED MODULE)")
            # in 'if' block, get_target_property() produces an error
            if Version(self.version) >= "4.4.0":
                replace_in_file(self, find_protobuf,
                                'if(TARGET "${Protobuf_LIBRARIES}")',
                                'if(FALSE)  # patch: disable if(TARGET "${Protobuf_LIBRARIES}")')

        # Patches in opencv_contrib
        # -------------------------

        ## Remove unused extra modules to avoid side effects
        if not self.options.with_cuda:
            rmdir(self, os.path.join(self._extra_modules_folder, "cudev"))
        for module in OPENCV_EXTRA_MODULES_OPTIONS:
            if not self.options.get_safe(module):
                rmdir(self, os.path.join(self._extra_modules_folder, module))
        for module in ["cnn_3dobj", "julia", "matlab"]:
            rmdir(self, os.path.join(self._extra_modules_folder, module))

        ## Fix Freetype discovery logic in freetype extra module
        if self.options.freetype:
            freetype_cmake = os.path.join(self._extra_modules_folder, "freetype", "CMakeLists.txt")
            replace_in_file(self, freetype_cmake, "ocv_check_modules(FREETYPE freetype2)", "find_package(Freetype REQUIRED MODULE)")
            replace_in_file(self, freetype_cmake, "FREETYPE_", "Freetype_")
            replace_in_file(self, freetype_cmake, "ocv_check_modules(HARFBUZZ harfbuzz)", "find_package(harfbuzz REQUIRED CONFIG)")
            replace_in_file(self, freetype_cmake, "HARFBUZZ_", "harfbuzz_")

        if self.options.get_safe("with_qt"):
            # Use proper CMake targets for Qt. Fails due to headers not being found otherwise.
            replace_in_file(self, os.path.join(self.source_folder, "modules", "highgui", "CMakeLists.txt"),
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
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        if os.path.isfile(os.path.join(self.package_folder, "setup_vars_opencv4.cmd")):
            mkdir(self, os.path.join(self.package_folder, "share"))
            rename(self, os.path.join(self.package_folder, "setup_vars_opencv4.cmd"),
                         os.path.join(self.package_folder, "share", "setup_vars_opencv4.cmd"))
        self._create_cmake_module_variables(os.path.join(self.package_folder, self._module_vars_rel_path))

    def _create_cmake_module_variables(self, module_file):
        """
        Define several CMake variables from upstream CMake config file not defined by default by CMakeDeps.
        See https://github.com/opencv/opencv/blob/4.8.1/cmake/templates/OpenCVConfig.cmake.in
        """
        v = Version(self.version)
        content = textwrap.dedent(f"""\
            if(NOT DEFINED OpenCV_LIBS)
                set(OpenCV_LIBS opencv::opencv)
            endif()
            if(NOT DEFINED OpenCV_VERSION_MAJOR)
                set(OpenCV_VERSION_MAJOR {v.major})
            endif()
            if(NOT DEFINED OpenCV_VERSION_MINOR)
                set(OpenCV_VERSION_MINOR {v.minor})
            endif()
            if(NOT DEFINED OpenCV_VERSION_PATCH)
                set(OpenCV_VERSION_PATCH {v.patch})
            endif()
        """)
        save(self, module_file, content)

    @property
    def _module_vars_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-variables.cmake")

    # returns true if GTK2 is selected. To do this, the version option
    # of the gtk/system package is checked or the conan package version
    # of an gtk conan package is checked.
    @property
    def _is_gtk_version2(self):
        if not self.options.get_safe("with_gtk", False):
            return False
        gtk_version = self.dependencies["gtk"].ref.version
        if gtk_version == "system":
            return self.dependencies["gtk"].options.version == 2
        else:
            return Version(gtk_version) < "3.0.0"

    @staticmethod
    def _cmake_target(module):
        if module in ("ippiw", "correspondence", "multiview", "numeric"):
            return module
        return f"opencv_{module}"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenCV")
        self.cpp_info.set_property("cmake_build_modules", [self._module_vars_rel_path])

        version = self.version.split(".")
        version = "".join(version) if self.settings.os == "Windows" else ""
        debug = "d" if self.settings.build_type == "Debug" and self.settings.os == "Windows" else ""

        def get_libs(module):
            if module == "ippiw":
                return [
                    f"{module}{debug}",
                    "ippicvmt" if self.settings.os == "Windows" else "ippicv",
                ]
            elif module in ("correspondence", "multiview", "numeric"):
                return [module]
            else:
                libs = [f"opencv_{module}{version}{debug}"]
                if module in ["core", "world"] and not self.options.shared:
                    lib_exclude_filter = "(opencv_|ippi|correspondence|multiview|numeric).*"
                    libs += list(filter(lambda x: not re.match(lib_exclude_filter, x), collect_libs(self)))
                return libs

        def add_components(modules):
            if self.options.world:
                self.cpp_info.components["opencv_world"].set_property("cmake_target_name", "opencv_world")
                self.cpp_info.components["opencv_world"].libs = get_libs("world")
                self.cpp_info.components["opencv_world"].resdirs = ["share"]
                if self.settings.os != "Windows":
                    self.cpp_info.components["opencv_world"].includedirs.append(os.path.join("include", "opencv4"))
                world_requires = set()
                world_requires_exclude = set()
                world_system_libs = set()
                world_frameworks = set()

            for module, values in modules.items():
                if not values.get("is_built"):
                    continue
                cmake_target = self._cmake_target(module)
                conan_component = cmake_target
                # TODO: we should also define COMPONENTS names of each target for find_package() but
                # not possible yet in CMakeDeps. See https://github.com/conan-io/conan/issues/10258
                self.cpp_info.components[conan_component].set_property("cmake_target_name", cmake_target)
                self.cpp_info.components[conan_component].resdirs = ["share"]
                if self.settings.os != "Windows":
                    self.cpp_info.components[conan_component].includedirs.append(os.path.join("include", "opencv4"))

                module_requires = values.get("requires", [])
                module_system_libs = []
                for _condition, _system_libs in values.get("system_libs", []):
                    if _condition:
                        module_system_libs.extend(_system_libs)
                module_frameworks = []
                for _condition, _frameworks in values.get("frameworks", []):
                    if _condition:
                        module_frameworks.extend(_frameworks)

                if self.options.world and values.get("is_part_of_world", True):
                    self.cpp_info.components[conan_component].requires = ["opencv_world"]
                    world_requires.update(module_requires)
                    world_requires_exclude.add(conan_component)
                    world_system_libs.update(module_system_libs)
                    world_frameworks.update(module_frameworks)
                else:
                    self.cpp_info.components[conan_component].libs = get_libs(module)
                    self.cpp_info.components[conan_component].requires = module_requires
                    self.cpp_info.components[conan_component].system_libs = module_system_libs
                    self.cpp_info.components[conan_component].frameworks = module_frameworks

            if self.options.world:
                self.cpp_info.components["opencv_world"].requires = list(world_requires - world_requires_exclude)
                self.cpp_info.components["opencv_world"].system_libs = list(world_system_libs)
                self.cpp_info.components["opencv_world"].frameworks = list(world_frameworks)

        add_components(self._opencv_modules)
