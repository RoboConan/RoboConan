import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime

required_conan_version = ">=2.1"


class Open3dConan(ConanFile):
    name = "open3d"
    description = "Open3D: A Modern Library for 3D Data Processing"
    license = "MIT"
    homepage = "https://github.com/isl-org/Open3D"
    topics = ("3d", "point-clouds", "visualization", "machine-learning", "rendering", "computer-graphics",
              "gpu", "cuda", "registration", "reconstruction", "odometry", "mesh-processing", "3d-perception")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_gui": [True, False],
        "with_cuda": [True, False],
        "with_openmp": [True, False],
        "with_ipp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_gui": False,
        "with_cuda": False,
        "with_openmp": True,
        "with_ipp": False,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda
        if self.options.get_safe("with_webrtc"):
            self.options.build_gui.value = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("assimp/[^5.4]")
        self.requires("blas/latest")
        self.requires("cppzmq/[^4]")
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        self.requires("embree/[^4]")
        self.requires("fmt/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("glew/[^2.2]")
        self.requires("glfw/[^3]", transitive_headers=True)
        self.requires("jsoncpp/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("lapack/latest", transitive_headers=True)
        self.requires("libcurl/[>=7.78 <9]")
        self.requires("libjpeg-meta/latest")
        self.requires("liblzf/[^3.6]")
        self.requires("libpng/[~1.6]")
        self.requires("minizip/[^1]")
        self.requires("msgpack-cxx/[>=3.3]", transitive_headers=True)
        self.requires("nanoflann/[^1.5]", transitive_headers=True, transitive_libs=True)
        self.requires("onetbb/[*]", transitive_headers=True, transitive_libs=True)
        self.requires("opengl/system", transitive_headers=True)
        self.requires("openssl/[>=1.1 <4]")
        self.requires("poissonrecon/12.00")
        self.requires("qhull/[^8.0]")
        self.requires("rply/[*]")
        self.requires("tinyfiledialogs/[^3]")
        self.requires("tinygltf/[^2.4.0]")
        self.requires("tinyobjloader/[^2, include_prerelease]")
        self.requires("uvatlas/[^1.9]")
        self.requires("vtk/[^9]", transitive_headers=True, transitive_libs=True)
        if self.options.build_gui:
            self.requires("filament/[^1.51]", transitive_headers=True, transitive_libs=True)
            self.requires("imgui/[^1.88]", transitive_headers=True, transitive_libs=True)
        if self.options.with_openmp:
            self.requires("openmp/system")
        if self.options.with_cuda:
            self.cuda.requires("cudart", transitive_headers=True)
            self.cuda.requires("cublas", transitive_libs=True)
            self.cuda.requires("cusolver", transitive_libs=True)
            self.requires("cutlass/[>=3 <5]", transitive_libs=True)
            self.requires("stdgpu/1.3.0-nvblox.20240211", transitive_headers=True, transitive_libs=True)
        if self.options.with_ipp:
            self.requires("intel-ipp/[*]", transitive_headers=True, transitive_libs=True)

        # if self.options.with_librealsense:
        #     self.requires("librealsense2/[^2.54]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)
        if self.dependencies["tinygltf"].options.header_only:
            raise ConanInvalidConfiguration("Open3D requires -o tinygltf/*:header_only=False")
        if self.options.get_safe("enable_headless_rendering"):
            if is_apple_os(self):
                raise ConanInvalidConfiguration(f"Headless rendering is not supported on {self.settings.os}")
            if self.options.build_gui:
                raise ConanInvalidConfiguration("enable_headless_rendering and build_gui cannot be enabled simultaneously")
        if self.options.with_cuda and self.options.get_safe("with_sycl"):
            raise ConanInvalidConfiguration("SYCL and CUDA cannot be enabled simultaneously")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.24]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")
        if self.options.build_gui:
            self.tool_requires("filament/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        rm(self, "find_dependencies.cmake", "3rdparty")
        for p in Path(self.source_folder, "3rdparty").iterdir():
            if p.is_dir() and p.name != "tomasakeninemoeller":
                rmdir(self, p)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_Open3D_INCLUDE"] = "conan_deps.cmake"
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_UNIT_TESTS"] = False
        tc.cache_variables["BUILD_BENCHMARKS"] = False
        tc.cache_variables["BUILD_PYTHON_MODULE"] = False
        tc.cache_variables["DEVELOPER_BUILD"] = False
        tc.cache_variables["BUILD_GUI"] = self.options.build_gui
        tc.cache_variables["ENABLE_HEADLESS_RENDERING"] = False  # requires OSMesa
        tc.cache_variables["STATIC_WINDOWS_RUNTIME"] = is_msvc_static_runtime(self)
        tc.cache_variables["GLIBCXX_USE_CXX11_ABI"] = self.settings.compiler.get_safe("libcxx") != "libstdc++"
        tc.cache_variables["USE_BLAS"] = self.dependencies["blas"].options.provider != "mkl"  # BLAS is always enabled, this only enables MKL-specific code
        tc.cache_variables["BUILD_AZURE_KINECT"] = False
        tc.cache_variables["BUILD_CUDA_MODULE"] = self.options.with_cuda
        tc.cache_variables["BUILD_ISPC_MODULE"] = False
        tc.cache_variables["BUILD_LIBREALSENSE"] = False
        tc.cache_variables["BUILD_PYTORCH_OPS"] = False
        tc.cache_variables["BUILD_SYCL_MODULE"] = False
        tc.cache_variables["BUILD_TENSORFLOW_OPS"] = False
        tc.cache_variables["BUILD_WEBRTC"] = self.options.get_safe("with_webrtc", False)
        tc.cache_variables["WITH_IPP"] = self.options.with_ipp
        tc.cache_variables["WITH_OPENMP"] = self.options.with_openmp
        tc.cache_variables["BUNDLE_OPEN3D_ML"] = False
        tc.cache_variables["FILAMENT_MATC"] = "matc"
        if self.options.with_cuda:
            tc.cache_variables["CMAKE_CUDA_ARCHITECTURES"] = str(self.settings.cuda.architectures).replace(",", ";")
            tc.preprocessor_definitions["FMT_USE_BITINT"] = "0"  # gets incorrectly enabled for NVCC
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("cppzmq", "cmake_target_name", "Open3D::3rdparty_cppzmq")
        deps.set_property("cub", "cmake_target_aliases", ["Open3D::3rdparty_cub"])
        deps.set_property("cutlass", "cmake_target_name", "Open3D::3rdparty_cutlass")
        deps.set_property("eigen", "cmake_target_name", "Open3D::3rdparty_eigen3")
        deps.set_property("fmt", "cmake_target_name", "Open3D::3rdparty_fmt")
        deps.set_property("glfw", "cmake_target_name", "Open3D::3rdparty_glfw")
        deps.set_property("gtest", "cmake_target_name", "Open3D::3rdparty_googletest")
        deps.set_property("jsoncpp", "cmake_target_name", "Open3D::3rdparty_jsoncpp")
        deps.set_property("k4a", "cmake_target_name", "Open3D::3rdparty_k4a")
        deps.set_property("librealsense", "cmake_target_name", "Open3D::3rdparty_librealsense")
        deps.set_property("msgpack-cxx", "cmake_target_name", "Open3D::3rdparty_msgpack")
        deps.set_property("msgpack-cxx", "cmake_file_name", "msgpack-cxx")
        deps.set_property("nanoflann", "cmake_target_name", "Open3D::3rdparty_nanoflann")
        deps.set_property("onedpl", "cmake_target_name", "Open3D::3rdparty_onedpl")
        deps.set_property("opengl", "cmake_target_name", "Open3D::3rdparty_opengl")
        deps.set_property("openmp", "cmake_target_name", "Open3D::3rdparty_openmp")
        deps.set_property("parallelstl", "cmake_target_name", "Open3D::3rdparty_parallelstl")
        deps.set_property("poissonrecon", "cmake_target_name", "Open3D::3rdparty_poissonrecon")
        deps.set_property("qhull", "cmake_target_name", "Open3D::3rdparty_qhull")
        deps.set_property("sycl", "cmake_target_name", "Open3D::3rdparty_sycl")
        deps.set_property("tinyfiledialogs", "cmake_target_name", "Open3D::3rdparty_tinyfiledialogs")
        deps.set_property("tinygltf", "cmake_target_name", "Open3D::3rdparty_tinygltf")
        deps.generate()

        if self.options.with_cuda:
            tc = self.cuda.CudaToolchain(self)
            tc.generate()
            # Needed to run ShaderEncoder built by the project
            if can_run(self):
                VirtualRunEnv(self).generate(scope="build")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Open3D")
        self.cpp_info.set_property("cmake_target_name", "Open3D::Open3D")

        self.cpp_info.libs = ["Open3D"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "winmm", "gdi32", "opengl32"]
        elif is_apple_os(self):
            self.cpp_info.frameworks = ["OpenGL", "Cocoa", "IOKit", "CoreVideo"]

        requires = [
            "assimp::assimp",
            "blas::blas",
            "cppzmq::cppzmq",
            "eigen::eigen",
            "embree::embree",
            "fmt::fmt",
            "glew::glew",
            "glfw::glfw",
            "jsoncpp::jsoncpp",
            "lapack::lapack",
            "libcurl::libcurl",
            "libjpeg-meta::libjpeg-meta",
            "liblzf::liblzf",
            "libpng::libpng",
            "minizip::minizip",
            "msgpack-cxx::msgpack-cxx",
            "nanoflann::nanoflann",
            "onetbb::onetbb",
            "opengl::opengl",
            "openssl::openssl",
            "poissonrecon::poissonrecon",
            "qhull::qhull",
            "rply::rply",
            "tinyfiledialogs::tinyfiledialogs",
            "tinygltf::tinygltf",
            "tinyobjloader::tinyobjloader",
            "uvatlas::uvatlas",
            "vtk::FiltersGeneral",
            "vtk::FiltersSources",
            "vtk::FiltersModeling",
            "vtk::FiltersCore",
            "vtk::CommonExecutionModel",
            "vtk::CommonDataModel",
            "vtk::CommonTransforms",
            "vtk::CommonMath",
            "vtk::CommonMisc",
            "vtk::CommonSystem",
            "vtk::CommonCore",
            "vtk::kissfft",
            "vtk::pugixml",
            "vtk::vtksys",
        ]
        if self.options.build_gui:
            requires += [
                "imgui::imgui",
                "filament::filament",
            ]
        if self.options.with_openmp:
            requires.append("openmp::openmp")
        if self.options.with_cuda:
            requires += [
            "cutlass::cutlass",
            "cudart::cudart",
            "cublas::cublas",
            "cusolver::cusolver",
            "stdgpu::stdgpu",
        ]
        self.cpp_info.requires = requires

        if not self.options.shared:
            self.cpp_info.defines.append("OPEN3D_STATIC")
        if self.options.with_cuda:
            self.cpp_info.defines.append("BUILD_CUDA_MODULE")
        if self.options.get_safe("with_ispc"):
            self.cpp_info.defines.append("BUILD_ISPC_MODULE")
        if self.options.get_safe("with_sycl"):
            self.cpp_info.defines.append("BUILD_SYCL_MODULE")
        if self.dependencies["blas"].options.provider != "mkl":
            self.cpp_info.defines.append("USE_BLAS")
        if self.options.with_ipp:
            self.cpp_info.defines.append("WITH_IPP")
