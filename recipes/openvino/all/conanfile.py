import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OpenvinoConan(ConanFile):
    name = "openvino"

    license = "Apache-2.0"
    homepage = "https://github.com/openvinotoolkit/openvino"
    description = "Open Visual Inference And Optimization toolkit for AI inference"
    topics = ("nlp", "natural-language-processing", "ai", "computer-vision", "deep-learning", "transformers", "inference",
              "speech-recognition", "yolo", "performance-boost", "diffusion-models", "recommendation-system", "stable-diffusion",
              "generative-ai", "llm-inference", "optimize-ai", "deploy-ai")
    package_id_non_embed_mode = "patch_mode"
    package_type = "library"
    no_copy_source = True

    # Binary configuration
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # HW plugins
        "enable_cpu": [True, False],
        "enable_gpu": [True, False],
        # SW plugins
        "enable_auto": [True, False],
        "enable_hetero": [True, False],
        "enable_auto_batch": [True, False],
        # Frontends
        "enable_ir_frontend": [True, False],
        "enable_onnx_frontend": [True, False],
        "enable_tf_frontend": [True, False],
        "enable_tf_lite_frontend": [True, False],
        "enable_paddle_frontend": [True, False],
        "enable_pytorch_frontend": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        # HW plugins
        "enable_cpu": True,
        "enable_gpu": True,
        # SW plugins
        "enable_auto": True,
        "enable_hetero": True,
        "enable_auto_batch": True,
        # Frontends
        "enable_ir_frontend": False,
        "enable_onnx_frontend": False,
        "enable_tf_frontend": False,
        "enable_tf_lite_frontend": False,
        "enable_paddle_frontend": False,
        "enable_pytorch_frontend": True,
    }

    @property
    def _protobuf_required(self):
        return self.options.enable_tf_frontend or self.options.enable_onnx_frontend or self.options.enable_paddle_frontend

    @property
    def _target_arm(self):
        return "arm" in self.settings.arch

    @property
    def _target_x86_64(self):
        return self.settings.arch == "x86_64"

    @property
    def _npu_option_available(self):
        return self.settings.os in ["Linux", "Windows"] and self._target_x86_64

    @property
    def _gpu_option_available(self):
        return self.settings.os != "Macos" and self._target_x86_64

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not self._gpu_option_available:
            del self.options.enable_gpu

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
            if self._protobuf_required:
                # even though OpenVINO can work with dynamic protobuf, it's still recommended to use static
                self.options["protobuf"].shared = False

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _dependency_versions(self):
        return self.conan_data["dependencies"][self.version]

    def _require(self, dependency):
        return f"{dependency}/{self._dependency_versions[dependency]}"

    def requirements(self):
        self.requires("onetbb/[>=2021 <2023]")
        self.requires("pugixml/[^1.14]")
        if Version(self.version) >= "2025.1.0":
                self.requires("nlohmann_json/3.11.3")
        if self._target_x86_64:
            self.requires("xbyak/6.73")
        if self.options.get_safe("enable_gpu"):
            self.requires("opencl-icd-loader/2023.04.17")
            self.requires("rapidjson/[>=0.0+git.20250205]")
        if self._protobuf_required:
            self.requires("protobuf/[>=3.21.12]")
        if self.options.enable_tf_frontend:
            self.requires("snappy/[^1.1.9]")
        if self.options.enable_onnx_frontend:
            self.requires(self._require("onnx"))
        if self.options.enable_tf_lite_frontend:
            self.requires("flatbuffers/23.5.26")

    def validate(self):
        if self.settings.os == "Emscripten":
            raise ConanInvalidConfiguration(f"{self.ref} does not support Emscripten")

    def build_requirements(self):
        if self._target_arm:
            self.tool_requires("scons/[^4.3.0]")
        if self._protobuf_required:
            self.tool_requires("protobuf/<host_version>")
        if self.options.enable_tf_lite_frontend:
            self.tool_requires("flatbuffers/<host_version>")
        if not self.options.shared:
            self.tool_requires("cmake/[>=3.18 <5]")

    def validate_build(self):
        min_cppstd = "17" if Version(self.version) >= "2025.0.0" else "11"
        check_min_cppstd(self, min_cppstd)

        # OpenVINO has unresolved symbols, when clang is used with libc++
        if self.settings.compiler == "clang" and self.settings.compiler.libcxx == "libc++":
            raise ConanInvalidConfiguration(
                f"{self.ref} cannot be built with clang and libc++ due to unresolved symbols. "
                f"Please, use libstdc++ instead."
            )

        # Failing on Conan Center CI due to memory usage
        if os.getenv("CONAN_CENTER_BUILD_SERVICE") and self.settings.build_type == "Debug":
            raise ConanInvalidConfiguration(f"{self.ref} does not support Debug build type on Conan Center CI")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["openvino"], strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["onednn_cpu"], strip_root=True, destination="src/plugins/intel_cpu/thirdparty/onednn")
        get(self, **self.conan_data["sources"][self.version]["mlas"], strip_root=True, destination="src/plugins/intel_cpu/thirdparty/mlas")
        get(self, **self.conan_data["sources"][self.version]["arm_compute"], strip_root=True, destination="src/plugins/intel_cpu/thirdparty/ComputeLibrary")
        get(self, **self.conan_data["sources"][self.version]["onednn_gpu"], strip_root=True, destination="src/plugins/intel_gpu/thirdparty/onednn_gpu")
        if Version(self.version) >= "2025.1.0":
            get(self, **self.conan_data["sources"][self.version]["arm_kleidiai"], strip_root=True, destination="src/plugins/intel_cpu/thirdparty/kleidiai")

        rmdir(self, "src/plugins/intel_gpu/thirdparty/rapidjson")
        # For CMake v4 support
        replace_in_file(self, "src/plugins/intel_cpu/thirdparty/onednn/CMakeLists.txt",
                        "cmake_minimum_required(VERSION 2.8.12)",
                        "cmake_minimum_required(VERSION 3.5)")
        # Disable docs
        save(self, "src/plugins/intel_cpu/thirdparty/onednn/cmake/doc.cmake", "")
        save(self, "src/plugins/intel_gpu/thirdparty/onednn_gpu/cmake/doc.cmake", "")

    def generate(self):
        tc = CMakeToolchain(self)
        # HW plugins
        tc.cache_variables["ENABLE_INTEL_CPU"] = self.options.enable_cpu
        if self._gpu_option_available:
            tc.cache_variables["ENABLE_INTEL_GPU"] = self.options.enable_gpu
            tc.cache_variables["ENABLE_ONEDNN_FOR_GPU"] = (
                self.options.enable_gpu
                or not self.options.enable_cpu
                or self.options.shared
            )
        if self._npu_option_available:
            tc.cache_variables["ENABLE_INTEL_NPU"] = False
        # SW plugins
        tc.cache_variables["ENABLE_AUTO"] = self.options.enable_auto
        tc.cache_variables["ENABLE_MULTI"] = self.options.enable_auto
        tc.cache_variables["ENABLE_AUTO_BATCH"] = self.options.enable_auto_batch
        tc.cache_variables["ENABLE_HETERO"] = self.options.enable_hetero
        # Frontends
        tc.cache_variables["ENABLE_OV_IR_FRONTEND"] = self.options.enable_ir_frontend
        tc.cache_variables["ENABLE_OV_PADDLE_FRONTEND"] = self.options.enable_paddle_frontend
        tc.cache_variables["ENABLE_OV_TF_FRONTEND"] = self.options.enable_tf_frontend
        tc.cache_variables["ENABLE_OV_TF_LITE_FRONTEND"] = self.options.enable_tf_lite_frontend
        tc.cache_variables["ENABLE_OV_ONNX_FRONTEND"] = self.options.enable_onnx_frontend
        tc.cache_variables["ENABLE_OV_PYTORCH_FRONTEND"] = self.options.enable_pytorch_frontend
        tc.cache_variables["ENABLE_OV_JAX_FRONTEND"] = False
        # Dependencies
        tc.cache_variables["ENABLE_SYSTEM_TBB"] = True
        tc.cache_variables["ENABLE_TBBBIND_2_5"] = False
        tc.cache_variables["ENABLE_SYSTEM_PUGIXML"] = True
        if self._protobuf_required:
            tc.cache_variables["ENABLE_SYSTEM_PROTOBUF"] = True
        if self.options.enable_tf_frontend:
            tc.cache_variables["ENABLE_SYSTEM_SNAPPY"] = True
        if self.options.enable_tf_lite_frontend:
            tc.cache_variables["ENABLE_SYSTEM_FLATBUFFERS"] = True
        if self.options.get_safe("enable_gpu"):
            tc.cache_variables["ENABLE_SYSTEM_OPENCL"] = True
        # misc
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["CPACK_GENERATOR"] = "CONAN"
        tc.cache_variables["ENABLE_PROFILING_ITT"] = False
        tc.cache_variables["ENABLE_PYTHON"] = False
        tc.cache_variables["ENABLE_PROXY"] = False
        tc.cache_variables["ENABLE_WHEEL"] = False
        tc.cache_variables["ENABLE_CPPLINT"] = False
        tc.cache_variables["ENABLE_NCC_STYLE"] = False
        tc.cache_variables["ENABLE_SAMPLES"] = False
        tc.cache_variables["ENABLE_TEMPLATE"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        for target in ["ov_frontends", "ov_plugins", "openvino_c"]:
            cmake.build(target=target)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # remove cmake and .pc files, since they will be generated later by Conan itself in package_info()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "config")
        self.cpp_info.set_property("cmake_file_name", "OpenVINO")
        self.cpp_info.set_property("pkg_config_name", "openvino")

        openvino_runtime = self.cpp_info.components["Runtime"]
        openvino_runtime.set_property("cmake_target_name", "openvino::runtime")
        openvino_runtime.requires = ["onetbb::libtbb", "pugixml::pugixml"]
        if Version(self.version) >= "2025.1.0":
            openvino_runtime.requires.append("nlohmann_json::nlohmann_json")
        openvino_runtime.libs = ["openvino"]
        if self._target_x86_64:
            openvino_runtime.requires.append("xbyak::xbyak")
        if self.settings.os in ["Linux", "Android", "FreeBSD", "SunOS", "AIX"]:
            openvino_runtime.system_libs = ["m", "dl", "pthread"]
        if self.settings.os == "Windows":
            openvino_runtime.system_libs.append("shlwapi")

        # Have to expose all internal libraries for static libraries case
        if not self.options.shared:
            # HW plugins
            if self.options.enable_cpu:
                openvino_runtime.libs.append("openvino_arm_cpu_plugin" if self._target_arm else \
                                             "openvino_intel_cpu_plugin")
                openvino_runtime.libs.extend(["openvino_onednn_cpu", "openvino_snippets", "mlas"])
                if self._target_arm:
                    openvino_runtime.libs.append("arm_compute-static")
                    if Version(self.version) >= "2025.1.0":
                        openvino_runtime.libs.append("kleidiai")
            if self.options.get_safe("enable_gpu"):
                openvino_runtime.libs.extend(["openvino_intel_gpu_plugin", "openvino_intel_gpu_graph",
                                              "openvino_intel_gpu_runtime", "openvino_intel_gpu_kernels"])
                openvino_runtime.libs.append("openvino_onednn_gpu")
            # SW plugins
            if self.options.enable_auto:
                openvino_runtime.libs.append("openvino_auto_plugin")
            if self.options.enable_hetero:
                openvino_runtime.libs.append("openvino_hetero_plugin")
            if self.options.enable_auto_batch:
                openvino_runtime.libs.append("openvino_auto_batch_plugin")
            # Frontends
            if self.options.enable_ir_frontend:
                openvino_runtime.libs.append("openvino_ir_frontend")
            if self.options.enable_onnx_frontend:
                openvino_runtime.libs.extend(["openvino_onnx_frontend", "openvino_onnx_common"])
                openvino_runtime.requires.extend(["protobuf::libprotobuf", "onnx::onnx"])
            if self.options.enable_tf_frontend:
                openvino_runtime.libs.extend(["openvino_tensorflow_frontend"])
                openvino_runtime.requires.extend(["protobuf::libprotobuf", "snappy::snappy"])
            if self.options.enable_tf_lite_frontend:
                openvino_runtime.libs.extend(["openvino_tensorflow_lite_frontend"])
                openvino_runtime.requires.extend(["flatbuffers::flatbuffers"])
            if self.options.enable_tf_frontend or self.options.enable_tf_lite_frontend:
                openvino_runtime.libs.extend(["openvino_tensorflow_common"])
            if self.options.enable_paddle_frontend:
                openvino_runtime.libs.append("openvino_paddle_frontend")
                openvino_runtime.requires.append("protobuf::libprotobuf")
            if self.options.enable_pytorch_frontend:
                openvino_runtime.libs.append("openvino_pytorch_frontend")
            # Common private dependencies should go last, because they satisfy dependencies for all other libraries
            openvino_runtime.libs.extend(["openvino_reference", "openvino_shape_inference", "openvino_itt",
                                          # utils goes last since all others depend on it
                                          "openvino_util"])
            if Version(self.version) >= "2025.1.0":
                openvino_runtime.libs.append("openvino_common_translators")
            # set 'openvino' once again for transformations objects files (cyclic dependency)
            # openvino_runtime.libs.append("openvino")
            full_openvino_lib_path = os.path.join(self.package_folder, "lib", "openvino.lib").replace("\\", "/") if self.settings.os == "Windows" else \
                                     os.path.join(self.package_folder, "lib", "libopenvino.a")
            openvino_runtime.system_libs.insert(0, full_openvino_lib_path)
            # Add definition to prevent symbols importing
            openvino_runtime.defines = ["OPENVINO_STATIC_LIBRARY"]

        if self.options.get_safe("enable_gpu"):
            openvino_runtime.requires.extend(["opencl-icd-loader::opencl-icd-loader", "rapidjson::rapidjson"])
            if self.settings.os == "Windows":
                openvino_runtime.system_libs.append("setupapi")

        openvino_runtime_c = self.cpp_info.components["Runtime_C"]
        openvino_runtime_c.set_property("cmake_target_name", "openvino::runtime::c")
        openvino_runtime_c.libs = ["openvino_c"]
        openvino_runtime_c.requires = ["Runtime"]

        def add_frontend_component(component_name, name, requires):
            component = self.cpp_info.components[component_name]
            component.set_property("cmake_target_name", f"openvino::frontend::{name}")
            component.libs = [f"openvino_{name}_frontend"]
            component.requires = ["Runtime"] + requires

        if self.options.enable_onnx_frontend:
            add_frontend_component("ONNX", "onnx", ["onnx::onnx", "protobuf::libprotobuf"])
        if self.options.enable_paddle_frontend:
            add_frontend_component("Paddle", "paddle", ["protobuf::libprotobuf"])
        if self.options.enable_tf_frontend:
            add_frontend_component("TensorFlow", "tensorflow", ["protobuf::libprotobuf", "snappy::snappy"])
        if self.options.enable_pytorch_frontend:
            add_frontend_component("PyTorch", "pytorch", [])
        if self.options.enable_tf_lite_frontend:
            add_frontend_component("TensorFlowLite", "tensorflow_lite", ["flatbuffers::flatbuffers"])

