from conan import ConanFile
from conan.tools.build import build_jobs, can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    @property
    def _tested_modules(self):
        return [
            # Main modules
            "calib", "core", "dnn", "features", "flann", "geometry", "highgui", "imgcodecs",
            "imgproc", "objdetect", "photo", "ptcloud", "stereo", "stitching", "video", "videoio",
            # Extra modules
            "alphamat", "bgsegm", "bioinspired", "ccalib", "datasets", "dnn_superres", "face",
            "freetype", "fuzzy", "gapi", "hdf", "hfs", "img_hash", "intensity_transform",
            "line_descriptor", "ml", "optflow", "phase_unwrapping", "plot", "quality", "reg",
            "rgbd", "saliency", "sfm", "shape", "signal", "structured_light", "superres",
            "surface_matching", "text", "tracking", "wechat_qrcode", "xfeatures2d",
            "ximgproc", "xobjdetect", "xphoto", "xstereo",
            # Modules that use the generic compile/link smoke test.
            "cudaarithm", "cudabgsegm", "cudacodec", "cudafeatures2d", "cudafilters",
            "cudaimgproc", "cudalegacy", "cudaobjdetect", "cudaoptflow", "cudastereo",
            "cudawarping", "cvv", "dnn_objdetect", "dpm", "ovis", "rapid", "videostab", "viz",
        ]

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TEST_OPENCV_WORLD"] = self.dependencies["opencv"].options.world
        tc.variables["TEST_OPENCV_SHARED"] = self.dependencies["opencv"].options.shared
        for module in self._tested_modules:
            cmake_option = f"OPENCV_WITH_{module.upper()}"
            if module == "core":
                tc.variables[cmake_option] = True
            else:
                tc.variables[cmake_option] = self.dependencies["opencv"].options.get_safe(module, False)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            with chdir(self, self.build_folder):
                self.run(f"ctest --output-on-failure -C {self.settings.build_type} -j {build_jobs(self)}", env="conanrun")
