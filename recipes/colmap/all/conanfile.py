import os
from pathlib import Path

from conan import ConanFile
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class ColmapConan(ConanFile):
    name = "colmap"
    description = ("COLMAP is a general-purpose Structure-from-Motion (SfM) and "
                   "Multi-View Stereo (MVS) pipeline with a graphical and command-line interface.")
    license = "BSD-3-Clause AND AGPL-3.0 AND BSD-2-Clause AND MIT AND DocumentRef-SiftGPU/LICENSE:LicenseRef-SiftGPU"
    homepage = "https://colmap.github.io/"
    topics = ("computer-vision", "structure-from-motion", "multi-view-stereo", "3d-reconstruction", "photogrammetry")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "fPIC": [True, False],
        "cgal": [True, False],
        "cuda": [True, False],
        "download": [True, False],
        "gui": [True, False],
        "ipo": [True, False],
        "lsd": [True, False],
        "openmp": [True, False],
        "tools": [True, False],
    }
    default_options = {
        "fPIC": True,
        "cgal": True,  # GPL-licensed
        "cuda": False,
        "download": True,
        "gui": False,
        "ipo": True,
        "lsd": True,  # AGPL-licensed
        "openmp": True,
        "tools": False,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest", "conan-utils/latest"
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    def configure(self):
        if not self.options.lsd:
            self.license = self.license.replace(" AND AGPL-3.0", "")
        if not self.options.cuda:
            del self.settings.cuda
        # Enable default options used by vcpkg.json in the project
        self.options["ceres-solver"].use_schur_specializations = True
        self.options["ceres-solver"].use_suitesparse = True
        self.options["ceres-solver"].use_lapack = True
        self.options["ceres-solver"].use_cuda = self.options.cuda
        self.options["boost"].with_program_options = True
        self.options["boost"].with_graph = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _crypto_package(self):
        if self.settings.os == "Windows" and self.settings.arch == "armv8":
            return "cryptopp"
        return "openssl"

    def requirements(self):
        self.requires("boost/[^1.71.0 <1.88]", transitive_headers=True, transitive_libs=True)
        self.requires("ceres-solver/[^2.2.0, include_prerelease]", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True, transitive_libs=True)
        self.requires("poselib/[^2.0.5]")
        self.requires("faiss/[^1.12.0]")
        self.requires("freeimage/[^3.19.21]")
        self.requires("glog/0.6.0", transitive_headers=True, transitive_libs=True)
        self.requires("metis/5.2.1")
        self.requires("sqlite3/[>=3.45.0 <4]", transitive_headers=True, transitive_libs=True)
        if self.options.download:
            self.requires("libcurl/[>=7.78 <9]")
            if self._crypto_package == "openssl":
                self.requires("openssl/[>=1.1 <4]")
            elif self._crypto_package == "cryptopp":
                self.requires("cryptopp/[^8.9.0]")
        if self.options.openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.cgal:
            self.requires("cgal/[^5.6.1]")
        if self.options.gui:
            # Qt6 is not supported
            self.requires("qt/[~5.15]", transitive_headers=True, transitive_libs=True)
        if self.options.gui or self.options.cuda:
            self.requires("glew/2.2.0")
            self.requires("opengl/system")
        if self.options.cuda:
            self.cuda.requires("cudart", transitive_headers=True, transitive_libs=True)
            self.cuda.requires("curand", transitive_headers=True, transitive_libs=True)
        # TODO: unvendor VLFeat, PoissonRecon, LSD, SiftGPU
        # self.requires("vlfeat/0.9.21", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.27 <5]")
        if self.options.gui:
            self.tool_requires("qt/<host_version>")
        if self.options.cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CUDA_STANDARD 17)", "")
        # Eigen v5 compatibility
        replace_in_file(self, "src/colmap/util/misc.h", "#include <algorithm>", "#include <algorithm>\n#include <cassert>")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CCACHE_ENABLED"] = False
        tc.cache_variables["CGAL_ENABLED"] = self.options.cgal
        tc.cache_variables["CUDA_ENABLED"] = self.options.cuda
        tc.cache_variables["DOWNLOAD_ENABLED"] = self.options.download
        tc.cache_variables["GUI_ENABLED"] = self.options.gui
        tc.cache_variables["IPO_ENABLED"] = self.options.ipo
        tc.cache_variables["LSD_ENABLED"] = self.options.lsd
        tc.cache_variables["OPENGL_ENABLED"] = self.options.gui
        tc.cache_variables["OPENMP_ENABLED"] = self.options.openmp
        tc.cache_variables["SIMD_ENABLED"] = True  # only applied to VLFeat and when on x86
        tc.cache_variables["TESTS_ENABLED"] = False
        tc.cache_variables["FETCH_FAISS"] = False
        tc.cache_variables["FETCH_POSELIB"] = False
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        if self.options.cuda and self.settings.os == "Linux" and not cross_building(self):
            # Workaround for -I/usr/include from OpenGL messing up the NVCC include dir search order,
            # causing src/thirdparty/SiftGPU/ProgramCU.cu to fail:
            #   /usr/include/c++/13/cmath:47:15: fatal error: math.h: No such file or directory
            #      47 | #include_next <math.h>
            # This variable is normally empty otherwise.
            tc.cache_variables["CMAKE_CUDA_IMPLICIT_INCLUDE_DIRECTORIES"] = "/usr/include"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("cgal", "cmake_file_name", "CGAL")
        deps.set_property("cgal", "cmake_target_aliases", ["CGAL"])
        deps.set_property("glew", "cmake_file_name", "Glew")
        deps.set_property("glew", "cmake_target_name", "GLEW::GLEW")
        deps.set_property("glog", "cmake_file_name", "Glog")
        deps.set_property("glog", "cmake_target_name", "glog::glog")
        deps.set_property("metis", "cmake_file_name", "Metis")
        deps.set_property("metis", "cmake_target_name", "metis")
        deps.generate()

        if self.options.cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def _patch_sources(self):
        for module in Path(self.source_folder, "cmake").glob("Find*.cmake"):
            if module.name != "FindDependencies.cmake":
                module.unlink()
        find_dependencies = Path(self.source_folder, "cmake", "FindDependencies.cmake")
        replace_in_file(self, find_dependencies, " QUIET", " REQUIRED")

        if not self.options.gui and not self.options.cuda:
            # OpenGL and GLEW are not actually being used in this case
            replace_in_file(self, find_dependencies, "find_package(Glew", "# find_package(Glew")
            replace_in_file(self, find_dependencies, "find_package(OpenGL", "# find_package(OpenGL")

        if not self.options.tools:
            replace_in_file(self, os.path.join(self.source_folder, "src", "colmap", "exe", "CMakeLists.txt"),
                            "COLMAP_ADD_EXECUTABLE(", "message(TRACE ")
            replace_in_file(self, os.path.join(self.source_folder, "src", "colmap", "exe", "CMakeLists.txt"),
                            "set_target_properties(colmap_main ", "# set_target_properties(colmap_main ")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        self._utils.limit_build_jobs(self, gb_mem_per_job=1)
        cmake.build()

    def package(self):
        copy(self, "COPYING.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*/LICENSE", os.path.join(self.source_folder, "src", "thirdparty"), os.path.join(self.package_folder, "licenses"))
        if not self.options.lsd:
            rmdir(self, os.path.join(self.package_folder, "licenses", "LSD"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "colmap")
        self.cpp_info.set_property("cmake_target_name", "colmap::colmap")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["COLMAP"])

        def _add_component(name, requires):
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", f"colmap::colmap_{name}")
            component.libs = [f"colmap_{name}"]
            component.requires = requires
            return component

        util = _add_component("util", requires=["boost::headers", "eigen::eigen", "glog::glog", "sqlite3::sqlite3"])
        _add_component("controllers", requires=["util", "estimators", "feature", "image", "math", "mvs", "retrieval", "sfm", "scene",
                                                "ceres-solver::ceres", "boost::program_options"])
        estimators = _add_component("estimators", requires=["util", "math", "feature_types", "geometry", "sensor", "image", "scene", "optim",
                                               "ceres-solver::ceres", "poselib::poselib"])
        exe = _add_component("exe", requires=["util", "controllers", "estimators", "geometry", "optim", "scene"])
        _add_component("feature_types", requires=["util"])
        feature = _add_component("feature", requires=["util", "feature_types", "geometry", "retrieval", "scene", "math", "sensor", "vlfeat",
                                                      "faiss::faiss_"])
        _add_component("geometry", requires=["util", "math"])
        image = _add_component("image", requires=["util", "sensor", "scene"])
        _add_component("math", requires=["util", "metis::metis", "boost::graph"])
        mvs = _add_component("mvs", requires=["util", "math", "scene", "sensor", "image", "poisson_recon"])
        _add_component("optim", requires=["math"])
        retrieval = _add_component("retrieval", requires=["math", "estimators", "optim", "faiss::faiss_"])
        _add_component("scene", requires=["util", "sensor", "feature_types", "geometry"])
        _add_component("sensor", requires=["util", "geometry", "vlfeat", "freeimage::freeimage", "ceres-solver::ceres"])
        _add_component("sfm", requires=["util", "geometry", "image", "scene", "estimators"])
        poisson_recon = _add_component("poisson_recon", requires=[])
        vlfeat = _add_component("vlfeat", requires=[])

        if self.options.lsd:
            _add_component("lsd", requires=[])
            image.requires.append("lsd")

        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < 9:
            self.cpp_info.system_libs.append("stdc++fs")

        if self.options.download:
            util.requires.append("libcurl::libcurl")
            if self._crypto_package == "openssl":
                util.requires.append("openssl::crypto")
            else:
                util.requires.append("cryptopp::cryptopp")

        if self.options.cgal:
            mvs.requires.append("cgal::cgal")

        if self.options.gui:
            _add_component("ui", requires=["util", "image", "scene", "controllers", "qt::qtCore", "qt::qtOpenGL", "qt::qtWidgets"])
            util.requires.extend(["qt::Core", "qt::OpenGL", "opengl::opengl"])
            feature.requires.extend(["qt::qtWidgets"])
            exe.requires.extend(["ui"])

        if self.options.openmp:
            poisson_recon.requires.append("openmp::openmp")
            retrieval.requires.append("openmp::openmp")
            vlfeat.requires.append("openmp::openmp")

        if self.options.cuda:
            # CUDA dependencies are exported in the CMake module
            _add_component("util_cuda", requires=["util", "cudart::cudart_"])
            _add_component("mvs_cuda", requires=["mvs", "util_cuda", "cudart::cudart_", "curand::curand"])
            estimators.requires.append("util_cuda")
            exe.requires.extend(["util_cuda", "mvs_cuda"])

        if self.options.gui or self.options.cuda:
            sift_gpu = _add_component("sift_gpu", requires=["opengl::opengl", "glew::glew"])
            feature.requires.extend(["sift_gpu"])
            if self.options.cuda:
                sift_gpu.requires.extend(["cudart::cudart_", "curand::curand"])
