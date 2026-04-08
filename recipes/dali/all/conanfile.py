import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd, check_min_cstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import *

required_conan_version = ">=2.1"


class DaliConan(ConanFile):
    name = "dali"
    description = ("The NVIDIA Data Loading Library (DALI) is a GPU-accelerated library for"
                   " data loading and pre-processing to accelerate deep learning applications")
    license = "Apache-2.0"
    homepage = "https://github.com/NVIDIA/DALI"
    topics = ("deep-learning", "machine-learning", "inference", "data-loading", "data-preprocessing", "gpu-acceleration", "cuda", "nvidia")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_awssdk": [True, False],
        "with_cfitsio": [True, False],
        "with_cufile": [True, False],
        "with_cvcuda": [True, False],
        "with_ffmpeg": [True, False],
        "with_ffts": [True, False],
        "with_jpeg": [True, False],
        "with_libsnd": [True, False],
        "with_libtar": [True, False],
        "with_lmdb": [True, False],
        "with_nvcomp": [True, False],
        "with_nvdec": [True, False],
        "with_nvjpeg": [True, False],
        "with_nvjpeg2k": [True, False],
        "with_nvml": [True, False],
        "with_nvof": [True, False],
        "with_tiff": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_awssdk": False,
        "with_cfitsio": False,
        "with_cufile": False,
        "with_cvcuda": False,
        "with_ffmpeg": False,
        "with_ffts": False,
        "with_jpeg": False,
        "with_libsnd": False,
        "with_libtar": False,
        "with_lmdb": False,
        "with_nvcomp": False,
        "with_nvdec": False,
        "with_nvjpeg": False,
        "with_nvjpeg2k": False,
        "with_nvml": False,
        "with_nvof": False,
        "with_tiff": False,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.with_nvdec:
            self.options.with_ffmpeg.value = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openmp/system")
        self.requires("rapidjson/[>=0.0+git.20250205]")
        self.requires("cocoapi/[*]")
        self.requires("cutlass/[^4]")
        self.requires("dlpack/[^1]")
        self.requires("boost/[^1.71]", libs=False)
        self.requires("protobuf/[>=3]")
        self.requires("opencv/[^4.9]")
        self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)
        self.cuda.requires("cufft")
        self.cuda.requires("curand", libs=False)
        self.cuda.requires("npp")
        self.requires("nvimgcodec/0.5.0")  # 0.6.0 is not yet supported as of v1.51.0
        self.requires("nvtx/[^3]")
        if self.options.with_cufile:
            self.cuda.requires("cufile")
        if self.options.with_cvcuda:
            self.requires("cv-cuda/[>=0.15.0 <1]")
        if self.options.with_nvdec:
            self.cuda.requires("nvidia-video-codec-sdk")
        if self.options.with_nvof:
            self.cuda.requires("nvidia-optical-flow-sdk")
        if self.options.with_nvjpeg:
            self.cuda.requires("nvjpeg")
        if self.options.with_nvjpeg2k:
            self.cuda.requires("nvjpeg2k")
        if self.options.with_nvml:
            self.cuda.requires("nvml-stubs")
        if self.options.with_nvcomp:
            self.requires("nvcomp/[^4]")
        if self.options.with_awssdk:
            self.requires("aws-sdk-cpp/[^1.9]")
        if self.options.with_cfitsio:
            self.requires("cfitsio/[^4]")
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/[*]")
        if self.options.with_ffts:
            self.requires("ffts/[>=0.9 <1]")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.with_libsnd:
            self.requires("libsndfile/[^1]")
        if self.options.with_libtar:
            self.requires("libtar/[^1]")
        if self.options.with_tiff:
            self.requires("libtiff/[^4.5]")
        if self.options.with_lmdb:
            self.requires("lmdb/[>=0.9 <1]")

    def validate(self):
        check_min_cppstd(self, 17)
        if self.settings.compiler.get_safe("cstd"):
            check_min_cstd(self, 11)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.18]")
        self.cuda.tool_requires("nvcc")
        self.tool_requires("protobuf/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

        # Respect architectures from the cuda.architectures setting
        replace_in_file(self, "CMakeLists.txt", "CUDA_get_cmake_cuda_archs(", "# CUDA_get_cmake_cuda_archs(")

        # Unvendor
        rmdir(self, "third_party/boost")
        replace_in_file(self, "dali/operators/reader/loader/coco_loader.h", "third_party/cocoapi/common/", "")
        replace_in_file(self, "dali/operators/reader/coco_reader_op.cc", "third_party/cocoapi/common/", "")
        replace_in_file(self, "dali/pipeline/data/dltensor.h", "third_party/dlpack/include/", "")
        replace_in_file(self, "dali/pipeline/data/dltensor_obj.h", "third_party/dlpack/include/", "")
        save(self, "cmake/Dependencies.cmake", "\nlink_libraries(CUDA::toolkit)\n", append=True)

        # Fix include / linking issues
        replace_in_file(self, "dali/CMakeLists.txt", "${DALI_PROTO_OBJ} ${CUDART_LIB}", "${DALI_PROTO_OBJ}")
        replace_in_file(self, "dali/core/CMakeLists.txt",
                        "${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES}/nvcomp",
                        "$<TARGET_PROPERTY:nvcomp::nvcomp_cpu,INTERFACE_INCLUDE_DIRECTORIES>/nvcomp")
        replace_in_file(self, "dali/core/CMakeLists.txt",
                        "${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES}/cufile.h",
                        "${cufile_INCLUDE_DIR}/cufile.h")
        replace_in_file(self, "dali/kernels/CMakeLists.txt", '"-Wl,--exclude-libs,', ") #")

        save(self, "dali/operators/reader/parser/CMakeLists.txt",
             "\ninclude_directories(${CMAKE_CURRENT_BINARY_DIR})\n"
             "target_link_libraries(CAFFE_PROTO protobuf::libprotobuf)\n"
             "target_link_libraries(CAFFE2_PROTO protobuf::libprotobuf)\n",
             append=True)
        replace_in_file(self, "dali/operators/reader/parser/caffe_parser.h",
                        "dali/operators/reader/parser/caffe.pb.h",
                        "dali/operators/reader/parser/proto/caffe.pb.h")
        replace_in_file(self, "dali/operators/reader/parser/caffe2_parser.h",
                        "dali/operators/reader/parser/caffe2.pb.h",
                        "dali/operators/reader/parser/proto/caffe2.pb.h")

        save(self, "dali/pipeline/CMakeLists.txt",
             "\ninclude_directories(${CMAKE_CURRENT_BINARY_DIR} ${CMAKE_BINARY_DIR})\n"
             "target_link_libraries(DALI_PROTO protobuf::libprotobuf)\n",
             append=True)
        for f in [
            "dali/pipeline/graph/cse.cc",
            "dali/pipeline/operator/checkpointing/checkpoint.cc",
            "dali/pipeline/operator/checkpointing/snapshot_serializer.cc",
            "dali/pipeline/pipeline.cc",
            "dali/pipeline/proto/dali_proto_intern.cc",
        ]:
            replace_in_file(self, f, "dali/pipeline/dali.pb.h", "dali/pipeline/proto/dali.pb.h")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TEST"] = False
        tc.cache_variables["BUILD_BENCHMARK"] = False
        tc.cache_variables["LINK_DRIVER"] = True
        tc.cache_variables["ENABLE_NVTX"] = True
        tc.cache_variables["BUILD_AWSSDK"] = self.options.with_awssdk
        tc.cache_variables["BUILD_CFITSIO"] = self.options.with_cfitsio
        tc.cache_variables["BUILD_CUFILE"] = self.options.with_cufile
        tc.cache_variables["BUILD_CVCUDA"] = self.options.with_cvcuda
        tc.cache_variables["BUILD_FFMPEG"] = self.options.with_ffmpeg
        tc.cache_variables["BUILD_FFTS"] = self.options.with_ffts
        tc.cache_variables["BUILD_JPEG_TURBO"] = self.options.with_jpeg
        tc.cache_variables["BUILD_LIBSND"] = self.options.with_libsnd
        tc.cache_variables["BUILD_LIBTAR"] = self.options.with_libtar
        tc.cache_variables["BUILD_LMDB"] = self.options.with_lmdb
        tc.cache_variables["BUILD_NVCOMP"] = self.options.with_nvcomp
        tc.cache_variables["BUILD_NVDEC"] = self.options.with_nvdec
        tc.cache_variables["BUILD_NVIMAGECODEC"] = True
        tc.cache_variables["BUILD_NVJPEG"] = self.options.with_nvjpeg
        tc.cache_variables["BUILD_NVJPEG2K"] = self.options.with_nvjpeg2k
        tc.cache_variables["BUILD_NVML"] = self.options.with_nvml
        tc.cache_variables["BUILD_NVOF"] = self.options.with_nvof
        tc.cache_variables["BUILD_TIFF"] = self.options.with_tiff
        tc.cache_variables["BUILD_PYTHON"] = False
        tc.cache_variables["WITH_DYNAMIC_NVJPEG"] = False
        tc.cache_variables["WITH_DYNAMIC_CUFFT"] = False
        tc.cache_variables["WITH_DYNAMIC_NPP"] = False
        tc.cache_variables["WITH_DYNAMIC_NVIMGCODEC"] = self.dependencies["nvimgcodec"].options.shared
        tc.cache_variables["WITH_DYNAMIC_NVCOMP"] = False
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        tc.preprocessor_definitions["NVIMGCODEC_DEFAULT_INSTALL_PATH"] = ""
        tc.cache_variables["Protobuf_USE_STATIC_LIBS"] = not self.dependencies["protobuf"].options.shared
        tc.cache_variables["BUILD_PROTO3"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("nvjpeg", "cmake_file_name", "NVJPEG")
        deps.set_property("nvjpeg", "cmake_find_mode", "both")
        deps.set_property("nvimgcodec", "cmake_target_aliases", ["nvImageCodec"])
        deps.set_property("lmdb", "cmake_file_name", "LMDB")
        deps.generate()

        cuda_tc = self.cuda.CudaToolchain()
        cuda_tc.generate()

        # Hacky fix for stub_codegen.py calls
        env = Environment()
        deps = ["cudart", "cuda-driver-stubs", "cuda-crt", "nvtx"]
        if self.options.with_nvml:
            deps.append("nvml-stubs")
        if self.options.with_nvcomp:
            deps.append("nvcomp")
        if self.options.with_cufile:
            deps.append("cufile")
        for dep in deps:
            env.append_path("CPATH", self.dependencies[dep].cpp_info.includedir)
        env.vars(self).save_script("cuda_cpath")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.components["dali_core"].libs = ["dali_core"]
        self.cpp_info.components["dali_core"].requires = ["cudart::cudart_"]
        if self.settings.os == "Linux":
            self.cpp_info.components["dali_core"].system_libs = ["m", "dl"]

        self.cpp_info.components["dali_kernels"].libs = ["dali_kernels"]
        requires = [
            "boost::headers",
            "cocoapi::cocoapi",
            "dlpack::dlpack",
            "opencv::opencv_imgcodecs",
            "opencv::opencv_imgproc",
            "openmp::openmp",
            "protobuf::protobuf",
            "rapidjson::rapidjson",
            "cutlass::cutlass",
            "cudart::cudart_",
            "curand::curand",
            "cufft::cufft_",
            "npp::npp",
            "nvtx::nvtx",
            "nvimgcodec::nvimgcodec",
        ]
        if self.options.with_awssdk:
            requires.append("aws-sdk-cpp::s3")
        if self.options.with_cfitsio:
            requires.append("cfitsio::cfitsio")
        if self.options.with_cufile:
            requires.append("cufile::cufile")
        if self.options.with_cvcuda:
            requires.append("cv-cuda::cv-cuda")
        if self.options.with_ffmpeg:
            requires.append("ffmpeg::ffmpeg")
        if self.options.with_ffts:
            requires.append("ffts::ffts")
        if self.options.with_jpeg:
            requires.append("libjpeg-meta::libjpeg-meta")
        if self.options.with_libsnd:
            requires.append("libsndfile::libsndfile")
        if self.options.with_libtar:
            requires.append("libtar::libtar")
        if self.options.with_lmdb:
            requires.append("lmdb::lmdb")
        if self.options.with_nvcomp:
            requires.extend(["nvcomp::nvcomp_", "nvcomp::nvcomp_cpu"])
        if self.options.with_nvdec:
            requires.append("nvidia-video-codec-sdk::nvidia-video-codec-sdk")
        if self.options.with_nvjpeg:
            requires.append("nvjpeg::nvjpeg")
        if self.options.with_nvjpeg2k:
            requires.append("nvjpeg2k::nvjpeg2k")
        if self.options.with_nvml:
            requires.append("nvml-stubs::nvml-stubs")
        if self.options.with_nvof:
            requires.append("nvidia-optical-flow-sdk::nvidia-optical-flow-sdk")
        if self.options.with_tiff:
            requires.append("libtiff::libtiff")
        self.cpp_info.components["dali_kernels"].requires = requires
        if self.settings.os == "Linux":
            self.cpp_info.components["dali_kernels"].system_libs = ["m", "dl"]

        self.cpp_info.components["dali_"].libs = ["dali"]
        self.cpp_info.components["dali_"].requires = ["dali_core", "dali_kernels"]

        self.cpp_info.components["dali_operators"].libs = ["dali_operators"]
        self.cpp_info.components["dali_operators"].requires = ["dali_"]
