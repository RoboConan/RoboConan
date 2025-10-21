import os
from functools import cached_property

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class PclConan(ConanFile):
    name = "pcl"
    description = ("The Point Cloud Library (PCL) is a standalone, large-scale, "
                   "open project for 2D/3D image and point cloud processing.")
    license = "BSD-3-Clause"
    homepage = "https://github.com/PointCloudLibrary/pcl"
    topics = ("computer vision", "point cloud", "pointcloud", "3d", "pcd", "ply", "stl", "ifs", "vtk")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        # Enable/disable individual components
        "2d": [True, False],
        "features": [True, False],
        "filters": [True, False],
        "geometry": [True, False],
        "io": [True, False],
        "kdtree": [True, False],
        "keypoints": [True, False],
        "ml": [True, False],
        "octree": [True, False],
        "outofcore": [True, False],
        "people": [True, False],
        "recognition": [True, False],
        "registration": [True, False],
        "sample_consensus": [True, False],
        "search": [True, False],
        "segmentation": [True, False],
        "simulation": [True, False],
        "stereo": [True, False],
        "surface": [True, False],
        "tracking": [True, False],
        "visualization": [True, False],
        "cuda_common": [True, False],
        "cuda_features": [True, False],
        "cuda_io": [True, False],
        "cuda_sample_consensus": [True, False],
        "cuda_segmentation": [True, False],
        "gpu_containers": [True, False],
        "gpu_features": [True, False],
        "gpu_kinfu": [True, False],
        "gpu_kinfu_large_scale": [True, False],
        "gpu_octree": [True, False],
        "gpu_people": [True, False],
        "gpu_segmentation": [True, False],
        "gpu_surface": [True, False],
        "gpu_tracking": [True, False],
        "gpu_utils": [True, False],
        "apps": [True, False],
        "tools": [True, False],
        # Optional external dependencies.
        # Only used if the corresponding component is enabled.
        "with_cuda": [True, False],
        "with_flann": [True, False],
        "with_libusb": [True, False],
        "with_nanoflann": [True, False],
        "with_opencv": [True, False],
        "with_opengl": [True, False],
        "with_openmp": [True, False],
        "with_openni2": [True, False],
        "with_pcap": [True, False],
        "with_png": [True, False],
        "with_qhull": [True, False],
        "with_qt": [True, False],
        "with_rssdk2": [True, False],
        "with_vtk": [True, False],
        "with_qvtk": [True, False],
        # TODO:
        # "with_metslib": [True, False],
        # "with_openni": [True, False],
        # Precompile for a minimal set of point types only instead of all (e.g., pcl::PointXYZ instead of PCL_XYZ_POINT_TYPES)
        "precompile_only_core_point_types": [True, False],
        # Whether to append a ''/d/rd/s postfix to executables on Windows depending on the build type
        "add_build_type_postfix": [True, False],
        "use_sse": [True, False],
        "use_avx": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        # Enable/disable individual components
        "2d": True,
        "features": True,
        "filters": True,
        "geometry": True,
        "io": True,
        "kdtree": True,
        "keypoints": True,
        "ml": True,
        "octree": True,
        "outofcore": False,
        "people": False,
        "recognition": True,
        "registration": True,
        "sample_consensus": True,
        "search": True,
        "segmentation": True,
        "simulation": False,
        "stereo": True,
        "surface": True,
        "tracking": True,
        "visualization": False,
        # GPU components are disabled by default
        "cuda_common": False,
        "cuda_features": False,
        "cuda_io": False,
        "cuda_sample_consensus": False,
        "cuda_segmentation": False,
        "gpu_containers": False,
        "gpu_features": False,
        "gpu_kinfu": False,
        "gpu_kinfu_large_scale": False,
        "gpu_octree": False,
        "gpu_people": False,
        "gpu_segmentation": False,
        "gpu_surface": False,
        "gpu_tracking": False,
        "gpu_utils": False,
        "apps": False,
        "tools": False,
        # Optional external dependencies
        "with_cuda": False,
        "with_flann": True,
        "with_libusb": False,
        "with_nanoflann": True,
        "with_opencv": True,
        "with_opengl": True,
        "with_openmp": True,
        "with_openni2": False,
        "with_pcap": False,
        "with_png": True,
        "with_qhull": True,
        "with_qt": True,
        "with_rssdk2": False,
        "with_vtk": False,
        "with_qvtk": False,
        # Enabled to avoid excessive memory usage during compilation in CCI
        "precompile_only_core_point_types": True,
        "add_build_type_postfix": False,
        "use_sse": True,
        "use_avx": True
    }

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    # The component details have been extracted from their CMakeLists.txt files using
    # https://gist.github.com/valgur/e54e39b6a8931b58cc1776515104c828
    @property
    def _external_deps(self):
        return {
            "common": ["boost", "eigen"],
            "cuda_common": ["cuda"],
            "cuda_features": ["cuda"],
            "cuda_io": ["cuda", "openni"],
            "cuda_sample_consensus": ["cuda"],
            "cuda_segmentation": ["cuda"],
            "gpu_containers": ["cuda"],
            "gpu_features": ["cuda"],
            "gpu_kinfu": ["cuda"],
            "gpu_kinfu_large_scale": ["cuda"],
            "gpu_octree": ["cuda"],
            "gpu_people": ["cuda"],
            "gpu_segmentation": ["cuda"],
            "gpu_surface": ["cuda"],
            "gpu_tracking": ["cuda"],
            "gpu_utils": ["cuda"],
            "io": ["zlib"],
            "people": ["vtk"],
            "surface": ["zlib"],
            "visualization": ["vtk"],
        }

    @property
    def _external_optional_deps(self):
        deps = {
            "2d": ["vtk"],
            "features": ["openmp"],
            "filters": ["openmp"],
            "io": ["libusb", "openmp", "openni", "openni2", "pcap", "png", "rssdk2", "vtk"],
            "kdtree": ["flann"],
            "keypoints": ["openmp"],
            "people": ["openni"],
            "recognition": ["metslib"],
            "registration": ["openmp"],
            "search": ["flann"],
            "simulation": ["opengl"],
            "segmentation": ["openmp"],
            "surface": ["openmp", "qhull", "vtk"],
            "tracking": ["openmp"],
            "visualization": ["opengl", "openni", "openni2"],
            "apps": ["cuda", "libusb", "opengl", "openni", "png", "qhull", "qt", "vtk"],
            "tools": ["cuda", "opencv", "opengl", "openni", "openni2", "qhull", "vtk"],
        }
        if Version(self.version) >= "1.15.1":
            deps["kdtree"].append("nanoflann")
        return deps

    def _ext_dep_to_conan_target(self, dep):
        if not self._is_enabled(dep):
            return []
        return {
            "boost": ["boost::headers", "boost::filesystem", "boost::iostreams"],
            "cuda": ["cudart::cudart_", "cuda-cccl::cuda-cccl"],
            "eigen": ["eigen::eigen"],
            "flann": ["flann::flann"],
            "libusb": ["libusb::libusb"],
            "metslib": [],
            "nanoflann": ["nanoflann::nanoflann"],
            "opencv": ["opencv::opencv"],
            "opengl": ["opengl::opengl", "freeglut::freeglut", "glew::glew", "glu::glu"],
            "openmp": ["openmp::openmp"],
            "openni": [],
            "openni2": ["openni2::openni2"],
            "pcap": ["libpcap::libpcap"],
            "png": ["libpng::libpng"],
            "qhull": ["qhull::qhull"],
            "qt": ["qt::qt"],
            "rssdk2": ["librealsense::librealsense"],
            "vtk": ["vtk::vtk"],
            "zlib": ["zlib-ng::zlib-ng"],
        }[dep]

    @cached_property
    def _internal_deps(self):
        deps = {
            "2d": ["common", "filters"],
            "common": [],
            "cuda_common": [],
            "cuda_features": ["common", "cuda_common", "io"],
            "cuda_io": ["common", "cuda_common", "io"],
            "cuda_sample_consensus": ["common", "cuda_common", "io"],
            "cuda_segmentation": ["common", "cuda_common", "io"],
            "features": ["2d", "common", "filters", "kdtree", "octree", "search"],
            "filters": ["common", "kdtree", "octree", "sample_consensus", "search"],
            "geometry": ["common"],
            "gpu_containers": ["common"],
            "gpu_features": ["common", "geometry", "gpu_containers", "gpu_octree", "gpu_utils"],
            "gpu_kinfu": ["common", "geometry", "gpu_containers", "io", "search"],
            "gpu_kinfu_large_scale": ["common", "features", "filters", "geometry", "gpu_containers",
                                      "gpu_utils", "io", "kdtree", "octree", "search", "surface"],
            "gpu_octree": ["common", "gpu_containers", "gpu_utils"],
            "gpu_people": ["common", "features", "filters", "geometry", "gpu_containers",
                           "gpu_utils", "io", "kdtree", "octree", "search", "segmentation",
                           "surface", "visualization"],
            "gpu_segmentation": ["common", "gpu_containers", "gpu_octree", "gpu_utils"],
            "gpu_surface": ["common", "geometry", "gpu_containers", "gpu_utils"],
            "gpu_tracking": ["common", "filters", "gpu_containers", "gpu_octree",
                             "gpu_utils", "kdtree", "octree", "search", "tracking"],
            "gpu_utils": ["common", "gpu_containers"],
            "io": ["common", "octree"],
            "kdtree": ["common"],
            "keypoints": ["common", "features", "filters", "kdtree", "octree", "search"],
            "ml": ["common"],
            "octree": ["common"],
            "outofcore": ["common", "filters", "io", "octree"],
            "people": ["common", "filters", "geometry", "io", "kdtree", "octree",
                       "sample_consensus", "search", "segmentation", "visualization"],
            "recognition": ["common", "features", "filters", "io", "kdtree", "ml",
                            "octree", "registration", "sample_consensus", "search"],
            "registration": ["common", "features", "filters", "kdtree", "octree",
                             "sample_consensus", "search"],
            "sample_consensus": ["common", "search"],
            "search": ["common", "kdtree", "octree"],
            "segmentation": ["common", "features", "filters", "geometry", "kdtree",
                             "ml", "octree", "sample_consensus", "search"],
            "simulation": ["common", "features", "filters", "geometry", "io",
                           "kdtree", "octree", "search", "surface", "visualization"],
            "stereo": ["common", "io"],
            "surface": ["common", "kdtree", "octree", "search"],
            "tracking": ["common", "filters", "kdtree", "octree", "search"],
            "visualization": ["common", "geometry", "io", "kdtree", "octree", "search"],
        }
        if (self.options.outofcore and self.options.visualization) or Version(self.version) < "1.15":
            deps["outofcore"].append("visualization")
        return deps

    @cached_property
    def _internal_optional_deps(self):
        return {
            "apps": ["2d", "common", "cuda_common", "cuda_features", "cuda_io",
                     "cuda_sample_consensus", "cuda_segmentation", "features", "filters",
                     "geometry", "io", "kdtree", "keypoints", "ml", "octree", "recognition",
                     "registration", "sample_consensus", "search", "segmentation", "stereo",
                     "surface", "tracking", "visualization"],
            "tools": ["features", "filters", "geometry", "gpu_kinfu", "gpu_kinfu_large_scale",
                      "io", "kdtree", "keypoints", "ml", "octree", "recognition", "registration",
                      "sample_consensus", "search", "segmentation", "surface", "visualization"],
        }

    def _enabled_internal_optional_deps(self, name):
        deps = self._internal_optional_deps.get(name, [])
        return [dep for dep in deps if self.options.get_safe(dep)]

    def _is_header_only(self, component):
        return component in {"2d", "cuda_common", "geometry"}

    @property
    def _extra_libs(self):
        return {"io": ["pcl_io_ply"]}

    def _enabled_components(self, opts=None):
        opts = opts or self.options
        return {c for c in self._internal_deps if opts.get_safe(c)} | {"common"}

    def _disabled_components(self, opts=None):
        opts = opts or self.options
        return {c for c in self._internal_deps if not opts.get_safe(c)} - {"common"}

    def _used_ext_deps(self, opts):
        all_deps = set()
        for component in self._enabled_components(opts):
            all_deps.update(self._external_deps.get(component, []))
            all_deps.update(self._external_optional_deps.get(component, []))
        return all_deps

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.use_sse
            del self.options.use_avx

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cuda:
            del self.settings.cuda
        if not self.options.with_vtk:
            del self.options.with_qvtk
        if Version(self.version) < "1.15.1":
            del self.options.with_nanoflann
        self.options["boost"].with_filesystem = True
        self.options["boost"].with_iostreams = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def _is_enabled(self, dep):
        always_available = ["boost", "eigen", "zlib"]
        is_available = self.options.get_safe(f"with_{dep}") or dep in always_available
        is_used = dep in self._used_ext_deps(self.options)
        return is_available and is_used

    def requirements(self):
        if Version(self.version) >= "1.15":
            self.requires("boost/[^1.71.0]", transitive_headers=True)
        else:
            # asio on 1.87 is not compatible
            self.requires("boost/[^1.71.0 <1.87]", transitive_headers=True)
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        if self._is_enabled("flann"):
            self.requires("flann/[^1.9.2]", transitive_headers=True)
        if self._is_enabled("png"):
            self.requires("libpng/[~1.6]")
        if self._is_enabled("qhull"):
            self.requires("qhull/8.1.alpha4", transitive_headers=True)
        if self._is_enabled("qt"):
            self.requires("qt/[>=6.6 <7]")
        if self._is_enabled("libusb"):
            self.requires("libusb/[^1.0.26]", transitive_headers=True)
        if self._is_enabled("nanoflann"):
            self.requires("nanoflann/[^1]", transitive_headers=True)
        if self._is_enabled("pcap"):
            self.requires("libpcap/[^1.10.4]")
        if self._is_enabled("opengl"):
            # OpenGL is only used if VTK is available
            self.requires("opengl/system", transitive_headers=True)
            self.requires("freeglut/[^3.4.0]", transitive_headers=True)
            self.requires("glew/2.2.0", transitive_headers=True)
            self.requires("glu/system", transitive_headers=True)
        if self._is_enabled("opencv"):
            self.requires("opencv/[^4.5]", transitive_headers=True)
        if self._is_enabled("zlib"):
            self.requires("zlib-ng/[^2.0]")
        if self._is_enabled("openmp"):
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self._is_enabled("openni2"):
            self.requires("openni2/[^2.2.0]", transitive_headers=True)
        if self.options.with_vtk:
            self.requires("vtk/[^9]", transitive_headers=True, options={
                "ChartsCore": "YES",
                "FiltersExtraction": "YES",
                "FiltersGeometry": "YES",
                "FiltersModeling": "YES",
                "FiltersSources": "YES",
                "FiltersStatistics": "YES",
                "GUISupportQt": "YES" if self.options.with_qvtk else "NO",
                "IOCore": "YES",
                "IOGeometry": "YES",
                "IOImage": "YES",
                "IOLegacy": "YES",
                "IOPLY": "YES",
                "IOXML": "YES",
                "IOXMLParser": "YES",
                "ImagingCore": "YES",
                "ImagingSources": "YES",
                "InteractionImage": "YES",
                "InteractionStyle": "YES",
                "InteractionWidgets": "YES",
                "ParallelDIY": "YES",
                "RenderingAnnotation": "YES",
                "RenderingContext2D": "YES",
                "RenderingContextOpenGL2": "YES",
                "RenderingCore": "YES",
                "RenderingFreeType": "YES",
                "RenderingLOD": "YES",
                "RenderingOpenGL2": "YES",
                "RenderingQt": "YES" if self.options.with_qvtk else "NO",
                "ViewsContext2D": "YES",
                "ViewsCore": "YES",
                "with_diy2": True,
                "with_eigen": True,
                "with_expat": True,
                "with_freetype": True,
                "with_glew": True,
                "with_nlohmannjson": True,
                "with_qt": self.options.with_qt,
            })
        if self._is_enabled("rssdk2"):
            self.requires("librealsense/[^2.49.0]")
        if self._is_enabled("cuda"):
            if Version(self.version) < "1.15.1" and self.cuda.major == 12:
                self.requires("cuda-cccl/[^2 <2.8]")
            else:
                self.cuda.requires("cuda-cccl")
            self.cuda.requires("cudart")
            if self.options.gpu_people:
                self.cuda.requires("npp")
            if self.options.gpu_tracking:
                self.cuda.requires("curand")

        # TODO:
        # self.requires("openni/x.x.x", transitive_headers=True)
        # self.requires("metslib/x.x.x", transitive_headers=True)
        # self.requires("opennurbs/x.x.x", transitive_headers=True)
        # self.requires("poisson4/x.x.x", transitive_headers=True)

    def package_id(self):
        used_deps = self._used_ext_deps(self.info.options)
        # Disable options that have no effect
        all_opts = [opt for opt, value in self.info.options.items()]
        for opt in all_opts:
            if opt.startswith("with_") and opt.split("_", 1)[1] not in used_deps:
                setattr(self.info.options, opt, False)

    def validate(self):
        enabled_components = self._enabled_components()
        for component in sorted(enabled_components):
            for dep in self._external_deps.get(component, []):
                if not self._is_enabled(dep):
                    raise ConanInvalidConfiguration(
                        f"'with_{dep}=True' is required when '{component}' is enabled."
                    )
            for dep in self._internal_deps[component]:
                if dep not in enabled_components:
                    raise ConanInvalidConfiguration(
                        f"'{dep}=True' is required when '{component}' is enabled."
                    )
        check_min_cppstd(self, 17)
        if self._is_enabled("cuda"):
            self.cuda.validate_settings()
            if self.cuda.major >= 13 and Version(self.version) < "1.15.1":
                raise ConanInvalidConfiguration("CUDA 13 or newer is only supported since PCL 1.15.1")
            if self.cuda.major >= 12:
                for mod in ["gpu_people", "gpu_kinfu", "gpu_kinfu_large_scale"]:
                    if self.options.get_safe(mod):
                        raise ConanInvalidConfiguration(f"{mod} module does not support CUDA 12 or newer")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.with_cuda:
            self.cuda.tool_requires("nvcc")
            self.tool_requires("cmake/[>=3.18]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

        # Let Conan set these
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD", "# set(CMAKE_CXX_STANDARD")
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CUDA_STANDARD", "# set(CMAKE_CUDA_STANDARD")
        replace_in_file(self, "CMakeLists.txt", "set(PCL_CXX_COMPILE_FEATURES", "# set(PCL_CXX_COMPILE_FEATURES")

        # Fix CUDA library dirs not being set
        replace_in_file(self, "cmake/pcl_find_cuda.cmake",
                        "set(CUDA_TOOLKIT_INCLUDE ${CUDAToolkit_INCLUDE_DIRS})",
                        "set(CUDA_TOOLKIT_INCLUDE ${CUDAToolkit_INCLUDE_DIRS})\n"
                        "link_directories(${CUDAToolkit_LIBRARY_DIR})")

        # Fix a missing curand dep
        replace_in_file(self, "gpu/tracking/CMakeLists.txt",
                        "pcl_gpu_containers",
                        "pcl_gpu_containers CUDA::curand")

        if Version(self.version) >= "1.15.1":
            replace_in_file(self, "CMakeLists.txt", "find_package(nanoflann 1.4.2 QUIET)", "find_package(nanoflann)")

        find_modules_to_remove = [
            "ClangFormat",
            "DSSDK",
            "Ensenso",
            "FLANN",
            "GLEW",
            "GTestSource",
            "OpenMP",
            "OpenNI",
            "OpenNI2",
            "Pcap",
            "Qhull",
            "RSSDK",
            "RSSDK2",
            "Sphinx",
            "davidSDK",
            "libusb",
        ]
        if Version(self.version) < "1.14.0":
            find_modules_to_remove.append("Eigen")
        for mod in find_modules_to_remove:
            rm(self, f"Find{mod}.cmake", os.path.join(self.source_folder, "cmake", "Modules"))

        # Don't need to call autoinit for VTK from Conan
        replace_in_file(self, "visualization/CMakeLists.txt",
                        "vtk_module_autoinit(",
                        "message(TRACE # vtk_module_autoinit(")

        # Let users activate/deactivate the AVX/SSE optimizations without depending on extra flags
        # added by Conan or downstream
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        'if(PCL_ENABLE_AVX AND "${CMAKE_CXX_FLAGS}" STREQUAL "${CMAKE_CXX_FLAGS_DEFAULT}")',
                        'if(PCL_ENABLE_AVX)')
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        'if(PCL_ENABLE_SSE AND "${CMAKE_CXX_FLAGS}" STREQUAL "${CMAKE_CXX_FLAGS_DEFAULT}")',
                        'if(PCL_ENABLE_SSE)')

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["PCL_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["WITH_LIBUSB"] = self._is_enabled("libusb")
        tc.cache_variables["WITH_OPENGL"] = self._is_enabled("opengl")
        tc.cache_variables["WITH_OPENMP"] = self._is_enabled("openmp")
        tc.cache_variables["WITH_PCAP"] = self._is_enabled("pcap")
        tc.cache_variables["WITH_PNG"] = self._is_enabled("png")
        tc.cache_variables["WITH_QHULL"] = self._is_enabled("qhull")
        if self._is_enabled("qhull"):
            # Upstream FindQhull.cmake defines HAVE_QHULL which changes content of pcl_config.h
            # Since we use CMakeDeps instead of this file, we have to manually inject HAVE_QHULL
            tc.cache_variables["HAVE_QHULL"] = True
        tc.cache_variables["WITH_QT"] = self._is_enabled("qt")
        tc.cache_variables["WITH_VTK"] = self._is_enabled("vtk")
        tc.cache_variables["WITH_CUDA"] = self._is_enabled("cuda")
        tc.cache_variables["BUILD_CUDA"] = self._is_enabled("cuda")
        tc.cache_variables["BUILD_GPU"] = self._is_enabled("cuda")
        tc.cache_variables["CUDA_ARCH_BIN"] = ";"
        tc.cache_variables["WITH_SYSTEM_ZLIB"] = True
        if not is_msvc(self):
            # PCL_ONLY_CORE_POINT_TYPES is always defined for MSVC and MinGW
            # Avoid warning C4005: 'PCL_ONLY_CORE_POINT_TYPES': macro redefinition message
            tc.cache_variables["PCL_ONLY_CORE_POINT_TYPES"] = self.options.precompile_only_core_point_types
        # The default False setting breaks OpenGL detection in CMake
        tc.cache_variables["PCL_ALLOW_BOTH_SHARED_AND_STATIC_DEPENDENCIES"] = True
        tc.cache_variables["OpenGL_GL_PREFERENCE"] = "GLVND"

        if not self.options.add_build_type_postfix:
            tc.cache_variables["CMAKE_DEBUG_POSTFIX"] = ""
            tc.cache_variables["CMAKE_RELEASE_POSTFIX"] = ""
            tc.cache_variables["CMAKE_RELWITHDEBINFO_POSTFIX"] = ""
            tc.cache_variables["CMAKE_MINSIZEREL_POSTFIX"] = ""

        tc.cache_variables["BUILD_tools"] = self.options.tools
        tc.cache_variables["BUILD_apps"] = self.options.apps
        tc.cache_variables["BUILD_examples"] = False
        enabled = sorted(self._enabled_components())
        disabled = sorted(self._disabled_components())
        self.output.info("Enabled components: " + ", ".join(enabled))
        self.output.info("Disabled components: " + ", ".join(disabled))
        for comp in enabled:
            tc.cache_variables[f"BUILD_{comp}"] = True
        for comp in disabled:
            tc.cache_variables[f"BUILD_{comp}"] = False

        tc.cache_variables["PCL_ENABLE_SSE"] = self.options.get_safe("use_sse", False)
        tc.cache_variables["PCL_ENABLE_AVX"] = self.options.get_safe("use_avx", False)
        # Let's skip the AVX2 check as it fails when cross-building from ARM to AMD
        # because of the -march=native flag, but -mavx2 actually works
        tc.cache_variables["HAVE_AVX2"] = self.options.get_safe("use_avx", False)

        # Do not overwrite CMakeToolchain variables with cache variables
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.cache_variables["CMAKE_CXX_STANDARD"] = str(self.settings.compiler.cppstd).replace("gnu", "")
        tc.generate()

        deps = CMakeDeps(self)
        if Version(self.version) < "1.14.0":
            deps.set_property("eigen", "cmake_file_name", "EIGEN")
        deps.set_property("flann", "cmake_file_name", "FLANN")
        deps.set_property("flann", "cmake_target_name", "FLANN::FLANN")
        deps.set_property("libpcap", "cmake_file_name", "PCAP")
        deps.set_property("qhull", "cmake_file_name", "QHULL")
        deps.set_property("qhull", "cmake_target_name", "QHULL::QHULL")
        deps.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        if self.options.with_cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)
        # Remove MSVC runtime libraries
        for dll_pattern_to_remove in ["concrt*.dll", "msvcp*.dll", "vcruntime*.dll"]:
            rm(self, dll_pattern_to_remove, os.path.join(self.package_folder, "bin"))

    @property
    def _version_suffix(self):
        semver = Version(self.version)
        return f"{semver.major}.{semver.minor}"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PCL")
        self.cpp_info.set_property("cmake_target_name", "PCL::PCL")
        self.cpp_info.set_property("cmake_find_mode", "both")

        for name in sorted(self._enabled_components()):
            component = self.cpp_info.components[name]
            component.set_property("cmake_file_name", name)
            component.set_property("cmake_module_file_name", name)
            component.set_property("cmake_target_name", f"PCL::{name}")
            component.set_property("pkg_config_name", f"pcl_{name}-{self._version_suffix}")
            component.includedirs = [os.path.join("include", f"pcl-{self._version_suffix}")]
            if not self._is_header_only(name):
                component.libs = [f"pcl_{name}"]
                component.libs += self._extra_libs.get(name, [])
            component.requires += self._internal_deps[name]
            component.requires += self._enabled_internal_optional_deps(name)
            for dep in self._external_deps.get(name, []) + self._external_optional_deps.get(name, []):
                component.requires += self._ext_dep_to_conan_target(dep)

        if self.options.apps:
            component = self.cpp_info.components["apps"]
            component.libs = []
            component.includedirs = []
            component.requires = self._enabled_internal_optional_deps("apps")
            for dep in self._external_optional_deps["apps"]:
                component.requires += self._ext_dep_to_conan_target(dep)

        if self.options.tools:
            component = self.cpp_info.components["tools"]
            component.libs = []
            component.includedirs = []
            component.requires = self._enabled_internal_optional_deps("tools")
            for dep in self._external_optional_deps["tools"]:
                component.requires += self._ext_dep_to_conan_target(dep)

        if self.options.kdtree and self.options.get_safe("with_nanoflann"):
            self.cpp_info.components["kdtree"].defines.append("PCL_HAS_NANOFLANN")

        if self.options.gpu_people:
            self.cpp_info.components["gpu_people"].requires.extend(["npp::nppim", "npp::nppidei", "npp::npps"])
        if self.options.gpu_tracking:
            self.cpp_info.components["gpu_tracking"].requires.append("curand::curand")

        if self.options.get_safe("use_sse"):
            # Assuming SSE4.2 extensions
            if not is_msvc(self):
                self.cpp_info.cxxflags.append("-msse4.2")
        if self.options.get_safe("use_avx"):
            # Assuming AVX2
            self.cpp_info.cxxflags.append("/arch:AVX2" if is_msvc(self) else "-mavx2")

        common = self.cpp_info.components["common"]
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                common.system_libs.append("pthread")
        if self.settings.os == "Windows":
            common.system_libs.append("ws2_32")
