import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.21"


class GtsamPointsPackage(ConanFile):
    name = "gtsam_points"
    description = "A collection of GTSAM factors and optimizers for range-based SLAM"
    license = "MIT"
    homepage = "https://github.com/koide3/gtsam_points"
    topics = ("localization", "mapping", "gpu", "cuda", "point-cloud", "registration", "slam", "factor-graph")

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "openmp": [True, False],
        "tbb": [True, False],
        "cuda": [True, False],
    }
    default_options = {
        "openmp": True,
        "tbb": False,
        "cuda": False,
        "boost/*:with_filesystem": True,
        "boost/*:with_graph": True,
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def configure(self):
        if not self.options.cuda:
            del self.settings.cuda

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True, transitive_libs=True)
        self.requires("gtsam/[^4.2]", transitive_headers=True, transitive_libs=True)
        self.requires("nanoflann/[~1.3]", transitive_headers=True, transitive_libs=True)
        self.requires("boost/[^1.71.0]", transitive_headers=True, transitive_libs=True)
        if self.options.openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.tbb:
            self.requires("onetbb/[>=2021 <2023]")
        if self.options.cuda:
            self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)
        if self.options.openmp and self.options.tbb:
            raise ConanInvalidConfiguration("Cannot enable both openmp and tbb options at the same time.")
        if self.options.cuda:
            self.cuda.validate_settings()
        for comp in ["filesystem", "graph"]:
            if not self.dependencies["boost"].options.get_safe(f"with_{comp}"):
                raise ConanInvalidConfiguration(f"-o boost/*:with_{comp}=True is required")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.24 <5]")
        if self.options.cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Unvendor nanoflann
        rmdir(self, os.path.join(self.source_folder, "thirdparty"))
        # Let Conan manage the C++ standard and also the CUDA standard indirectly
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        # Let CudaToolchain manage the CUDA architecture
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CUDA_ARCHITECTURES", "# set(CMAKE_CUDA_ARCHITECTURES")
        # Don't build utility functions for cusparse and curand that are not used anywhere
        replace_in_file(self, "CMakeLists.txt", " src/gtsam_points/cuda/check_error_cusolver.cu", "")
        replace_in_file(self, "CMakeLists.txt", " src/gtsam_points/cuda/check_error_curand.cu", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_WITH_MARCH_NATIVE"] = False
        tc.variables["BUILD_WITH_OPENMP"] = self.options.openmp
        tc.variables["BUILD_WITH_TBB"] = self.options.tbb
        tc.variables["BUILD_WITH_CUDA"] = self.options.cuda
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("gtsam", "cmake_target_name", "GTSAM::GTSAM")
        deps.generate()

        if self.options.cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gtsam_points")
        self.cpp_info.set_property("cmake_extra_variables", {
            "GTSAM_POINTS_USE_TBB": "ON" if self.options.tbb else "OFF",
            "GTSAM_POINTS_USE_OPENMP": "ON" if self.options.openmp else "OFF",
            "GTSAM_POINTS_USE_CUDA": "ON" if self.options.cuda else "OFF",
        })

        gtsam_points = self.cpp_info.components["libgtsam_points"]
        gtsam_points.set_property("cmake_target_name", "gtsam_points::gtsam_points")
        gtsam_points.libs = ["gtsam_points"]
        requires = [
            "boost::headers",
            "boost::filesystem",
            "boost::graph",
            "eigen::eigen",
            "gtsam::gtsam",
            "nanoflann::nanoflann",
        ]
        if self.options.openmp:
            requires.append("openmp::openmp")
        if self.options.tbb:
            requires.append("onetbb::libtbb")
        gtsam_points.requires += requires

        if self.options.cuda:
            gtsam_points_cuda = self.cpp_info.components["gtsam_points_cuda"]
            gtsam_points_cuda.set_property("cmake_target_name", "gtsam_points::gtsam_points_cuda")
            gtsam_points_cuda.libs = ["gtsam_points_cuda"]
            gtsam_points_cuda.requires = requires + ["cudart::cudart_"]
            gtsam_points.requires.append("gtsam_points_cuda")
