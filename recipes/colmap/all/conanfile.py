import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
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
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "caspar": [False, "float", "double"],
        "cgal": [True, False],
        "cuda": [True, False],
        "download": [True, False],
        "gui": [True, False],
        "hash_map": ["std", "boost"],
        "ipo": [True, False],
        "lsd": [True, False],
        "mvs": [True, False],
        "onnx": [True, False],
        "openmp": [True, False],
        "simd": [True, False],
        "tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "caspar": False,
        "cgal": True,  # GPL-licensed
        "cuda": False,
        "download": True,
        "gui": False,
        "hash_map": "std",
        "ipo": True,
        "lsd": True,  # AGPL-licensed
        "mvs": True,
        "onnx": False,
        "openmp": True,
        "simd": True,
        "tools": False,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest", "conan-utils/latest"
    python_requires_extend = "conan-cuda.Cuda"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.lsd:
            self.license = self.license.replace(" AND AGPL-3.0", "")
        if not self.options.gui and not self.options.cuda:
            self.license = self.license.replace(" AND DocumentRef-SiftGPU/LICENSE:LicenseRef-SiftGPU", "")
        if self.options.caspar:
            self.license += " AND Apache-2.0"
        if not self.options.mvs:
            self.options.rm_safe("cgal")
        if not self.options.cuda:
            del self.settings.cuda
        # Enable default options used by vcpkg.json in the project
        self.options["ceres-solver"].use_schur_specializations = True
        self.options["ceres-solver"].use_suitesparse = True
        self.options["ceres-solver"].use_lapack = True
        self.options["ceres-solver"].use_cuda = self.options.cuda
        self.options["boost"].with_program_options = True
        self.options["boost"].with_graph = True
        if self.options.gui:
            self.options["qt"].qtsvg = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _crypto_package(self):
        if self.settings.os == "Windows" and self.settings.arch == "armv8":
            return "cryptopp"
        return "openssl"

    def requirements(self):
        self.requires("boost/[^1.71.0]", transitive_headers=True, transitive_libs=True)
        self.requires("ceres-solver/[^2.2.0, include_prerelease]", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True, transitive_libs=True)
        self.requires("poselib/[>=3 <4, include_prerelease]")
        self.requires("faiss/[>=1.12 <1.13]")
        self.requires("openimageio/[>=3 <4]", transitive_headers=True, transitive_libs=True)
        self.requires("glog/[>=0.6 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("metis/[^5]")
        self.requires("sqlite3/[>=3.45.0 <4]", transitive_headers=True, transitive_libs=True)
        self.requires("suitesparse-cholmod/[^5]", transitive_headers=True, transitive_libs=True)
        if self.options.download:
            self.requires("libcurl/[>=7.78 <9]")
            if self._crypto_package == "openssl":
                self.requires("openssl/[<5]")
            elif self._crypto_package == "cryptopp":
                self.requires("cryptopp/[^8.9.0]")
        if self.options.openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.get_safe("cgal"):
            self.requires("cgal/[>=5.6.1 <7]")
        if self.options.onnx:
            self.requires("onnxruntime/[>=1.22.2 <2]")
        if self.options.gui:
            self.requires("qt/[>=5.15 <7]", transitive_headers=True, transitive_libs=True)
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
        if self.options.caspar and not self.options.cuda:
            raise ConanInvalidConfiguration("Caspar requires CUDA")
        if self.options.caspar:
            self.cuda.check_min_cuda_architecture(75)
        if self.options.hash_map == "boost" and self.dependencies["boost"].ref.version < "1.84":
            raise ConanInvalidConfiguration("The Boost hash map backend requires Boost 1.84 or newer")
        if self.options.cuda:
            self.cuda.validate_settings()

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.27 <5]")
        if self.options.gui:
            self.tool_requires("qt/<host_version>")
        if self.options.cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ALL_SOURCE_TARGET"] = False
        tc.cache_variables["ASAN_ENABLED"] = False
        tc.cache_variables["BENCHMARK_ENABLED"] = False
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["CASPAR_ENABLED"] = bool(self.options.caspar)
        tc.cache_variables["CASPAR_USE_DOUBLE"] = self.options.caspar == "double"
        tc.cache_variables["CCACHE_ENABLED"] = False
        tc.cache_variables["CGAL_ENABLED"] = self.options.get_safe("cgal", False)
        tc.cache_variables["COLMAP_HASH_MAP_BACKEND"] = str(self.options.hash_map).upper()
        tc.cache_variables["COVERAGE_ENABLED"] = False
        tc.cache_variables["CUDA_ENABLED"] = self.options.cuda
        tc.cache_variables["DOWNLOAD_ENABLED"] = self.options.download
        tc.cache_variables["FETCH_FAISS"] = False
        tc.cache_variables["FETCH_ONNX"] = False
        tc.cache_variables["FETCH_POSELIB"] = False
        tc.cache_variables["GUI_ENABLED"] = self.options.gui
        tc.cache_variables["HIP_ENABLED"] = False
        tc.cache_variables["IPO_ENABLED"] = self.options.ipo
        tc.cache_variables["LSD_ENABLED"] = self.options.lsd
        tc.cache_variables["MVS_ENABLED"] = self.options.mvs
        tc.cache_variables["ONNX_ENABLED"] = self.options.onnx
        tc.cache_variables["OPENGL_ENABLED"] = self.options.gui
        tc.cache_variables["OPENMP_ENABLED"] = self.options.openmp
        tc.cache_variables["PROFILING_ENABLED"] = False
        tc.cache_variables["SIMD_ENABLED"] = self.options.simd
        tc.cache_variables["TESTS_ENABLED"] = False
        tc.cache_variables["TSAN_ENABLED"] = False
        tc.cache_variables["UBSAN_ENABLED"] = False
        tc.cache_variables["UNINSTALL_ENABLED"] = False
        tc.cache_variables["WERROR_ENABLED"] = False
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        if self.options.download:
            tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_CURL"] = True
            if self._crypto_package == "openssl":
                tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_OpenSSL"] = True
            else:
                tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_CryptoPP"] = True
        if self.options.cuda:
            tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_CUDAToolkit"] = True
        if self.options.cuda and self.settings.os == "Linux" and not cross_building(self):
            # Workaround for -I/usr/include from OpenGL messing up the NVCC include dir search order,
            # causing src/thirdparty/SiftGPU/ProgramCU.cu to fail:
            #   /usr/include/c++/13/cmath:47:15: fatal error: math.h: No such file or directory
            #      47 | #include_next <math.h>
            # This variable is normally empty otherwise.
            tc.cache_variables["CMAKE_CUDA_IMPLICIT_INCLUDE_DIRECTORIES"] = "/usr/include"
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.get_safe("cgal"):
            deps.set_property("cgal", "cmake_file_name", "CGAL")
            deps.set_property("cgal", "cmake_target_aliases", ["CGAL"])
        if self.options.gui or self.options.cuda:
            deps.set_property("glew", "cmake_file_name", "Glew")
            deps.set_property("glew", "cmake_target_name", "GLEW::GLEW")
        if self.options.download and self._crypto_package == "cryptopp":
            deps.set_property("cryptopp", "cmake_file_name", "CryptoPP")
        deps.set_property("glog", "cmake_file_name", "Glog")
        deps.set_property("glog", "cmake_target_name", "glog::glog")
        deps.set_property("metis", "cmake_file_name", "Metis")
        deps.set_property("metis", "cmake_target_name", "metis")
        deps.set_property("suitesparse-cholmod", "cmake_file_name", "CHOLMOD")
        deps.set_property("suitesparse-cholmod", "cmake_target_name", "CHOLMOD::CHOLMOD")
        deps.generate()

        if self.options.cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def _patch_sources(self):
        for module in Path(self.source_folder, "cmake").glob("Find*.cmake"):
            if module.name != "FindDependencies.cmake":
                module.unlink()
        find_dependencies = Path(self.source_folder, "cmake", "FindDependencies.cmake")

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
        rmdir(self, os.path.join(self.package_folder, "share", "colmap"))
        if not self.options.tools or not self.options.gui:
            rmdir(self, os.path.join(self.package_folder, "share", "applications"))
            rmdir(self, os.path.join(self.package_folder, "share", "icons"))
        if not self.options.tools and self.settings.os == "Windows":
            rm(self, "COLMAP.bat", self.package_folder)
            rm(self, "RUN_TESTS.bat", self.package_folder)
        for test_header in (
            "geometry/rigid3_matchers.h",
            "geometry/sim3_matchers.h",
            "scene/reconstruction_matchers.h",
            "util/eigen_matchers.h",
        ):
            rm(self, test_header, os.path.join(self.package_folder, "include", "colmap"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "colmap")
        self.cpp_info.set_property("cmake_target_name", "colmap::colmap")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["COLMAP"])

        glog_version = Version(self.dependencies["glog"].ref.version)
        common_defines = [
            f"COLMAP_HASH_{str(self.options.hash_map).upper()}",
            f"GLOG_VERSION_MAJOR={glog_version.major}",
            f"GLOG_VERSION_MINOR={glog_version.minor}",
        ]
        if self.options.caspar:
            common_defines.append("CASPAR_ENABLED")
            if self.options.caspar == "double":
                common_defines.append("CASPAR_USE_DOUBLE")
        if self.options.get_safe("cgal"):
            common_defines.append("COLMAP_CGAL_ENABLED")
        if self.options.cuda:
            common_defines.append("COLMAP_CUDA_ENABLED")
        if self.options.download:
            common_defines.append("COLMAP_DOWNLOAD_ENABLED")
        if self.options.gui:
            common_defines.extend(["COLMAP_GUI_ENABLED", "COLMAP_GPU_ENABLED"])
        if self.options.lsd:
            common_defines.append("COLMAP_LSD_ENABLED")
        if self.options.mvs:
            common_defines.append("COLMAP_MVS_ENABLED")
        if self.options.onnx:
            common_defines.append("COLMAP_ONNX_ENABLED")
            if self.settings.os == "Macos":
                common_defines.append("COLMAP_COREML_ENABLED")
        if self.options.cuda and "COLMAP_GPU_ENABLED" not in common_defines:
            common_defines.append("COLMAP_GPU_ENABLED")

        def _add_component(name, requires, *, lib_name=None, target_name=None, interface=False):
            component = self.cpp_info.components[name]
            target_name = target_name or f"colmap_{name}"
            component.set_property("cmake_target_name", f"colmap::{target_name}")
            if not interface:
                component.libs = [lib_name or target_name]
                if self.options.shared and self.settings.os != "Windows":
                    component.libdirs = ["thirdparty"]
            component.requires = requires
            component.defines = list(common_defines)
            return component

        util = _add_component("util", requires=[
            "boost::headers", "eigen::eigen", "glog::glog", "openimageio::openimageio_openimageio",
        ])
        controllers = _add_component("controllers", requires=[
            "estimators", "feature", "retrieval", "geometry", "scene", "util",
            "image", "math", "sfm", "ceres-solver::ceres",
            "boost::headers", "boost::program_options", "faiss::faiss"
        ])
        estimators = _add_component("estimators", requires=[
            "util", "math", "feature_types", "geometry", "sensor", "image",
            "scene", "optim", "estimators_cost_functions", "estimators_solvers",
            "eigen::eigen", "ceres-solver::ceres", "poselib::poselib"
        ])
        _add_component("estimators_cost_functions", requires=[
                "geometry", "sensor", "eigen::eigen", "ceres-solver::ceres"
            ], interface=True)
        _add_component("estimators_solvers", requires=[
            "util", "math", "geometry", "scene", "optim", "estimators_cost_functions",
            "eigen::eigen", "ceres-solver::ceres", "poselib::poselib"
        ])
        exe = _add_component("exe", requires=[
            "controllers", "estimators", "geometry", "optim", "scene", "sfm", "util",
            "boost::headers"
        ])
        _add_component("feature_types", requires=["util", "eigen::eigen"])
        feature = _add_component("feature", requires=[
            "feature_types", "scene_types", "geometry", "util", "math", "sensor", "vlfeat",
            "eigen::eigen", "faiss::faiss"
        ])
        _add_component("geometry", requires=["util", "math", "eigen::eigen"])
        image = _add_component("image", requires=["scene", "util", "sensor", "vlfeat", "eigen::eigen"])
        _add_component("math", requires=["util", "boost::graph", "boost::headers", "eigen::eigen", "metis::metis"])
        optim = _add_component("optim", requires=["math", "util", "eigen::eigen", "suitesparse-cholmod::suitesparse-cholmod"])
        retrieval = _add_component("retrieval", requires=[
            "util", "math", "feature_types", "estimators", "optim",
            "boost::headers", "eigen::eigen", "faiss::faiss"
        ])
        _add_component("scene_types", requires=["sensor", "feature_types", "geometry", "util", "eigen::eigen"])
        _add_component("scene", requires=["scene_types", "util", "eigen::eigen", "sqlite3::sqlite3", "optim"])
        _add_component("sensor", requires=[
            "geometry", "util", "ceres-solver::ceres", "eigen::eigen",
            "openimageio::openimageio_openimageio"
        ])
        _add_component("sfm", requires=["scene", "estimators", "util", "geometry", "image"])
        poisson_recon = _add_component("poisson_recon", requires=[])
        vlfeat = _add_component("vlfeat", requires=[])

        if self.options.mvs:
            mvs = _add_component("mvs", requires=[
                "util", "scene", "math", "sensor", "image", "poisson_recon", "eigen::eigen"
            ])
            controllers.requires.append("mvs")
            exe.requires.append("mvs")

        if self.options.lsd:
            _add_component("lsd", requires=[])
            image.requires.append("lsd")

        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < 9:
            util.system_libs.append("stdc++fs")

        if self.options.download:
            util.requires.append("libcurl::libcurl")
            if self._crypto_package == "openssl":
                util.requires.append("openssl::crypto")
            else:
                util.requires.append("cryptopp::cryptopp")

        if self.options.get_safe("cgal"):
            mvs.requires.append("cgal::cgal")

        if self.options.onnx:
            feature.requires.append("onnxruntime::onnxruntime")

        if self.options.gui:
            qt_requires = ["qt::qtCore", "qt::qtOpenGL", "qt::qtSvg", "qt::qtWidgets"]
            if Version(self.dependencies["qt"].ref.version) >= "6":
                qt_requires.append("qt::qtOpenGLWidgets")
            ui_requires = ["util", "image", "scene", "controllers", *qt_requires]
            if self.options.mvs:
                ui_requires.append("mvs")
            _add_component("ui", ui_requires)
            util.requires.extend(["qt::qtCore", "qt::qtOpenGL", "opengl::opengl"])
            if Version(self.dependencies["qt"].ref.version) >= "6":
                util.requires.append("qt::qtOpenGLWidgets")
            exe.requires.append("ui")

        if self.options.openmp:
            poisson_recon.requires.append("openmp::openmp")
            feature.requires.append("openmp::openmp")
            optim.requires.append("openmp::openmp")
            retrieval.requires.append("openmp::openmp")
            vlfeat.requires.append("openmp::openmp")
            if self.options.mvs:
                mvs.requires.append("openmp::openmp")

        if self.options.cuda:
            _add_component("util_cuda", requires=["util", "cudart::cudart_", "curand::curand"])
            controllers.requires.append("util_cuda")
            estimators.requires.append("util_cuda")
            exe.requires.append("util_cuda")
            if self.options.mvs:
                _add_component("mvs_cuda", requires=["mvs", "util_cuda", "cudart::cudart_", "curand::curand"])
                controllers.requires.append("mvs_cuda")
                exe.requires.append("mvs_cuda")

        if self.options.caspar:
            caspar = _add_component("caspar_lib_core", requires=["cudart::cudart_"], target_name="caspar_lib_core")
            caspar.libdirs = ["lib"]
            estimators.requires.append("caspar_lib_core")

        if self.options.gui or self.options.cuda:
            sift_gpu = _add_component("sift_gpu", requires=["opengl::opengl", "glew::glew"])
            feature.requires.append("sift_gpu")
            if self.options.cuda:
                sift_gpu.requires.extend(["cudart::cudart_", "curand::curand"])
