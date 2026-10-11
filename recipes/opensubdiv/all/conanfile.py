import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class OpenSubdivConan(ConanFile):
    name = "opensubdiv"
    description = "An Open-Source subdivision surface library"
    license = "DocumentRef-LICENSE.txt:LicenseRef-OpenSubDivModified-Apache-2.0"
    homepage = "https://github.com/PixarAnimationStudios/OpenSubdiv"
    topics = ("cgi", "vfx", "animation", "subdivision surface")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tbb": [True, False],
        "with_opengl": [True, False],
        "with_omp": [True, False],
        "with_cuda": [True, False],
        "with_clew": [True, False],
        "with_opencl": [True, False],
        "with_dx": [True, False],
        "with_metal": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tbb": True,
        "with_opengl": True,
        "with_omp": False,
        "with_cuda": False,
        "with_clew": False,
        "with_opencl": False,
        "with_dx": False,
        "with_metal": True
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _min_cppstd(self):
        if self.options.get_safe("with_metal"):
            return "14"
        return "11"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            del self.options.with_dx
        if self.settings.os != "Macos":
            del self.options.with_metal

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_tbb:
            self.requires("onetbb/[>=2021]", transitive_headers=True)
        if self.options.with_opengl:
            self.requires("opengl/system")
            self.requires("glfw/[^3.4]")
        if self.options.get_safe("with_metal"):
            self.requires("metal-cpp/14.2")
        if self.options.with_cuda:
            self.cuda.requires("cudart")

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)
        if self.options.shared and self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} shared not supported on Windows")
        if self.options.with_cuda:
            self.cuda.validate_settings()

    def build_requirements(self):
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # No warnings as errors
        replace_in_file(self, "CMakeLists.txt", "/WX", "")

    @property
    def _osd_gpu_enabled(self):
        return any([
            self.options.with_opengl,
            self.options.with_opencl,
            self.options.with_cuda,
            self.options.get_safe("with_dx"),
            self.options.get_safe("with_metal"),
        ])

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["NO_TBB"] = not self.options.with_tbb
        tc.variables["NO_OPENGL"] = not self.options.with_opengl
        tc.variables["BUILD_SHARED_LIBS"] = self.options.get_safe("shared")
        tc.variables["NO_OMP"] = not self.options.with_omp
        tc.variables["NO_CUDA"] = not self.options.with_cuda
        tc.variables["NO_DX"] = not self.options.get_safe("with_dx")
        tc.variables["NO_METAL"] = not self.options.get_safe("with_metal")
        tc.variables["NO_CLEW"] = not self.options.with_clew
        tc.variables["NO_OPENCL"] = not self.options.with_opencl
        tc.variables["NO_PTEX"] = True  # Note: PTEX is for examples only, but we skip them..
        tc.variables["NO_DOC"] = True
        tc.variables["NO_EXAMPLES"] = True
        tc.variables["NO_TUTORIALS"] = True
        tc.variables["NO_REGRESSION"] = True
        tc.variables["NO_TESTS"] = True
        tc.variables["NO_GLTESTS"] = True
        tc.variables["NO_MACOS_FRAMEWORK"] = True
        # Let Conan manage the CUDA arch flags
        tc.variables["OSD_CUDA_NVCC_FLAGS"] = ""
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def _patch_sources(self):
        if self.settings.os == "Macos" and not self._osd_gpu_enabled:
            path = os.path.join(self.source_folder, "opensubdiv", "CMakeLists.txt")
            replace_in_file(self, path, "$<TARGET_OBJECTS:osd_gpu_obj>", "")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenSubdiv")
        target_suffix = "" if self.options.shared else "_static"

        self.cpp_info.components["osdcpu"].set_property("cmake_target_name", f"OpenSubdiv::osdcpu{target_suffix}")
        self.cpp_info.components["osdcpu"].libs = ["osdCPU"]
        if self.options.with_tbb:
            self.cpp_info.components["osdcpu"].requires = ["onetbb::onetbb"]

        if self._osd_gpu_enabled:
            self.cpp_info.components["osdgpu"].set_property("cmake_target_name", f"OpenSubdiv::osdgpu{target_suffix}")
            self.cpp_info.components["osdgpu"].libs = ["osdGPU"]
            self.cpp_info.components["osdgpu"].requires = ["osdcpu"]
            if self.options.with_opengl:
                self.cpp_info.components["osdgpu"].requires.extend(["opengl::opengl", "glfw::glfw"])
            if self.options.get_safe("with_metal"):
                self.cpp_info.components["osdgpu"].requires.append("metal-cpp::metal-cpp")
            if self.options.with_cuda:
                self.cpp_info.components["osdgpu"].requires.append("cudart::cudart_")
            dl_required = self.options.with_opengl or self.options.with_opencl
            if self.settings.os in ["Linux", "FreeBSD"] and dl_required:
                self.cpp_info.components["osdgpu"].system_libs = ["dl"]
