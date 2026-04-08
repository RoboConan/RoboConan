import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class TensorflowLiteConan(ConanFile):
    name = "tensorflow-lite"
    description = ("TensorFlow Lite is a set of tools that enables on-device machine learning "
                   "by helping developers run their models on mobile, embedded, and IoT devices.")
    license = "Apache-2.0"
    homepage = "https://www.tensorflow.org/lite/guide"
    topics = ("machine-learning", "neural-networks", "deep-learning")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "use_mmap": [True, False],
        "with_nnapi": [True, False],
        "with_ruy": [True, False],
        "with_xnnpack": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "use_mmap": True,
        "with_nnapi": True,
        "with_ruy": True,
        "with_xnnpack": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src/tensorflow/lite"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.use_mmap
        if self.settings.os != "Android":
            del self.options.with_nnapi

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("abseil/[>=20230125.3]", transitive_headers=True, transitive_libs=True)
        self.requires("flatbuffers/24.3.25", transitive_headers=True)
        self.requires("protobuf/[*]")
        self.requires("eigen/[>=3.3 <6]")
        self.requires("farmhash/[>=0.0+git.20190513]")
        self.requires("fp16/[>=0.0+git.20210320]")
        self.requires("fxdiv/[>=0.0+git.20200417]")
        self.requires("gemmlowp/[>=0.0+git.20210928]")
        self.requires("ooura-fft/[>=0.0+git.20061228]")
        self.requires("pthreadpool/[>=0.0+git.20231129]")
        self.requires("ruy/[>=0.0+git.20231129]")
        if self.settings.arch in ["x86", "x86_64"]:
            self.requires("intel-neon2sse/[>=0.0+git.20210225]")
        if self.options.with_xnnpack:
            self.requires("xnnpack/[>=0.0+git.20231026]")

    def validate(self):
        check_min_cppstd(self, 20)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16]")
        self.tool_requires("protobuf/<host_version>")
        self.tool_requires("flatbuffers/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        cmakelists = "tensorflow/lite/CMakeLists.txt"
        save(self, cmakelists, "\n\ninstall(TARGETS tensorflow-lite LIBRARY DESTINATION lib ARCHIVE DESTINATION lib RUNTIME DESTINATION bin)", append=True)
        replace_in_file(self, cmakelists, "set(CMAKE_CXX_STANDARD 20)", "")
        replace_in_file(self, cmakelists, "find_package(ml_dtypes REQUIRED)", "")
        replace_in_file(self, cmakelists, "ml_dtypes", "")
        replace_in_file(self, cmakelists, "set(FLATBUFFERS_FLATC_EXECUTABLE", "# ")
        replace_in_file(self, cmakelists, 'DEPENDS "${FLATC_TARGET}"', "DEPENDS")
        replace_in_file(self, cmakelists, "IF(NOT DEFINED FP16_SOURCE_DIR)", "if(0)")
        # Unvendor fft2d
        replace_in_file(self, "tensorflow/lite/kernels/internal/spectrogram.cc", "third_party/fft2d/fft.h", "fft/fft.h")
        replace_in_file(self, "tensorflow/lite/kernels/internal/spectrogram.h", "third_party/fft2d/fft.h", "fft/fft.h")
        replace_in_file(self, "tensorflow/lite/kernels/irfft2d.cc", "third_party/fft2d/fft2d.h", "fft/fft2.h")
        replace_in_file(self, "tensorflow/lite/kernels/rfft2d.cc", "third_party/fft2d/fft2d.h", "fft/fft2.h")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_tensorflow-lite_INCLUDE"] = "conan_deps.cmake"
        tc.cache_variables["TFLITE_ENABLE_GPU"] = False
        tc.cache_variables["TFLITE_ENABLE_MMAP"] = self.options.get_safe("use_mmap", False)
        tc.cache_variables["TFLITE_ENABLE_NNAPI"] = self.options.get_safe("with_nnapi", False)
        tc.cache_variables["TFLITE_ENABLE_RUY"] = self.options.with_ruy
        tc.cache_variables["TFLITE_ENABLE_XNNPACK"] = self.options.with_xnnpack
        tc.cache_variables["SYSTEM_PTHREADPOOL"] = True
        tc.cache_variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        v = Version(self.version)
        tc.preprocessor_definitions["TF_MAJOR_VERSION"] = str(v.major)
        tc.preprocessor_definitions["TF_MINOR_VERSION"] = str(v.minor)
        tc.preprocessor_definitions["TF_PATCH_VERSION"] = str(v.patch)
        tc.preprocessor_definitions["TF_VERSION_SUFFIX"] = ""
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("farmhash", "cmake_target_name", "farmhash")
        deps.set_property("flatbuffers", "cmake_target_name", "flatbuffers::flatbuffers")
        deps.set_property("ooura-fft", "cmake_file_name", "fft2d")
        deps.set_property("ooura-fft", "cmake_target_name", "fft2d_fftsg2d")
        deps.set_property("xnnpack", "cmake_file_name", "XNNPACK")
        deps.generate()

    def build(self):
        if not self.options.with_xnnpack:
            cmakelists = os.path.join(self.source_folder, "tensorflow/lite/CMakeLists.txt")
            replace_in_file(self, cmakelists, "target_compile_options(xnnpack-delegate", "message(TRACE #")
        cmake = CMake(self)
        cmake.configure(build_script_folder="tensorflow/lite")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        for subdir in ["lite", "c", "cc", "core", "compiler"]:
            copy(self, "*.h",
                 os.path.join(self.source_folder, "tensorflow", subdir),
                 os.path.join(self.package_folder, "include", "tensorflow", subdir))
        copy(self, "*.h",
             os.path.join(self.build_folder, "tensorflow"),
             os.path.join(self.package_folder, "include", "tensorflow"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tensorflowlite")
        self.cpp_info.set_property("cmake_target_name", "tensorflow::tensorflowlite")
        self.cpp_info.libs = ["tensorflow-lite"]
        if not self.options.shared:
            self.cpp_info.defines.append("TFL_STATIC_LIBRARY_BUILD")
        if self.options.with_ruy:
            self.cpp_info.defines.append("TFLITE_WITH_RUY")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("dl")
