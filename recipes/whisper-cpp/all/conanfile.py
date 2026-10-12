import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class WhisperCppConan(ConanFile):
    name = "whisper-cpp"
    description = "High-performance inference of OpenAI's Whisper automatic speech recognition (ASR) model"
    license = "MIT"
    homepage = "https://github.com/ggerganov/whisper.cpp"
    topics = ("whisper", "asr")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
        "with_cuda": [True, False],
        "with_openvino": [True, False],
        "with_coreml": [True, False],
        "coreml_allow_fallback": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": True,
        "with_cuda": False,
        "with_openvino": False,
        "with_coreml": False,
        "coreml_allow_fallback": False,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not is_apple_os(self):
            del self.options.with_coreml

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["ggml"].with_openmp = self.options.with_openmp
        if self.options.with_cuda:
            self.options["ggml"].with_cuda = True
        else:
            del self.settings.cuda
        if not self.options.get_safe("with_coreml"):
            del self.options.coreml_allow_fallback

    def requirements(self):
        self.requires("ggml/[>=0.9 <1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openvino:
            self.requires("openvino/[>=2024.5.0]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18 <5]")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["WHISPER_BUILD_TESTS"] = False
        tc.variables["WHISPER_BUILD_EXAMPLES"] = False
        tc.variables["WHISPER_BUILD_SERVER"] = False
        tc.variables["WHISPER_BUILD_IS_DEV"] = False
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["WHISPER_USE_SYSTEM_GGML"] = True
        tc.variables["WHISPER_USE_SYSTEM_LLAMA"] = False
        tc.variables["WHISPER_COMMON_FFMPEG"] = False
        tc.variables["WHISPER_CUDA"] = self.options.with_cuda
        tc.variables["WHISPER_OPENVINO"] = self.options.with_openvino
        tc.variables["WHISPER_COREML"] = self.options.get_safe("with_coreml", False)
        tc.variables["WHISPER_COREML_ALLOW_FALLBACK"] = self.options.get_safe("coreml_allow_fallback", False)
        tc.variables["WHISPER_VITISAI"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        if self.options.with_cuda:
            tc = self.cuda.CudaToolchain()
            tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        copy(self, "*",
             os.path.join(self.source_folder, "models"),
             os.path.join(self.package_folder, "share", self.name, "models"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "whisper")
        self.cpp_info.resdirs = ["share"]

        whisper = self.cpp_info.components["whisper"]
        whisper.set_property("cmake_target_name", "whisper")
        whisper.set_property("pkg_config_name", "whisper")
        whisper.libs = ["whisper"]
        whisper.requires = ["ggml::ggml_"]

        parakeet = self.cpp_info.components["parakeet"]
        parakeet.set_property("cmake_target_name", "parakeet")
        parakeet.set_property("pkg_config_name", "parakeet")
        parakeet.libs = ["parakeet"]
        parakeet.requires = ["ggml::ggml_"]

        if self.options.get_safe("with_coreml"):
            coreml = self.cpp_info.components["whisper-coreml"]
            coreml.set_property("cmake_target_name", "whisper.coreml")
            coreml.libs = ["whisper.coreml"]
            coreml.frameworks = ["CoreML", "Foundation"]
            whisper.requires.append("whisper-coreml")

        if self.options.with_openvino:
            whisper.requires.append("openvino::Runtime")

        if self.settings.os in ["Linux", "FreeBSD"]:
            whisper.system_libs = ["dl", "m", "pthread"]
            parakeet.system_libs = ["dl", "m", "pthread"]
