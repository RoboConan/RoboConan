import glob
import os
import textwrap
from pathlib import Path

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OpenmvgConan(ConanFile):
    name = "openmvg"
    description = (
        "OpenMVG provides an end-to-end 3D reconstruction from images framework "
        "compounded of libraries, binaries, and pipelines."
    )
    license = "MPL-2.0"
    topics = ("computer-vision", "geometry", "structure-from-motion", "sfm",
              "multi-view-geometry", "photogrammetry", "3d-reconstruction")
    homepage = "https://github.com/openMVG/openMVG"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_ligt": [True, False],
        "programs": [True, False],
        "with_openmp": [True, False],
        "cpu_architecture": [
            "auto", "generic", "none",
            # Intel
            "core", "merom", "penryn", "nehalem", "westmere", "sandy-bridge", "ivy-bridge", "haswell",
            "broadwell", "skylake", "skylake-xeon", "kaby-lake", "cannonlake", "silvermont", "goldmont",
            "knl", "atom",
            # AMD
            "k8", "k8-sse3", "barcelona", "istanbul", "magny-cours", "bulldozer", "interlagos",
            "piledriver", "AMD 14h", "AMD 16h", "zen"
        ],
        "avx": [False, "avx", "avx2"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_ligt": False, # patent-protected and CC-BY-SA-licensed
        "programs": True,
        "with_openmp": True,
        "cpu_architecture": "sandy-bridge",  # sse sse2 sse3 ssse3 sse4.1 sse4.2 avx
        "avx": "avx",
    }

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src", "src"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if is_apple_os(self):
            # sse sse2 sse3 ssse3 sse4.1 sse4.2, no avx
            self.options.cpu_architecture = "westmere"
            self.options.avx = False
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.cpu_architecture
            del self.options.avx

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cereal/[^1.3.2]", transitive_headers=True)
        if Version(self.version) >= "2.1":
            self.requires("ceres-solver/[^2.2.0, include_prerelease]", transitive_headers=True)
            self.requires("spectra/[^1.0]")
        else:
            self.requires("ceres-solver/[~2.1]", transitive_headers=True)
        self.requires("coin-clp/[^1.17.9]")
        self.requires("coin-osi/[>=0.108.10 <1]")
        self.requires("coin-utils/[^2.11.11]")
        self.requires("coin-lemon/[^1.3.1]", transitive_headers=True, transitive_libs=True)
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        self.requires("flann/[^1]", transitive_headers=True, transitive_libs=True)
        self.requires("hnswlib/[<1]", transitive_headers=True)
        self.requires("easyexif/[1.0+openmvg.*]")
        self.requires("vlfeat/[>=0.9.21 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg-meta/latest")
        self.requires("libpng/[~1.6]")
        self.requires("libtiff/[>=4.5 <5]")
        if self.options.with_openmp:
            # '#pragma omp' is used in public headers
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        if self.version == "2.0":
            replace_in_file(self, "src/CMakeLists.txt",
                            "CMAKE_MINIMUM_REQUIRED(VERSION 3.1)",
                            "CMAKE_MINIMUM_REQUIRED(VERSION 3.5)")
        # Unvendor
        keep = ["fast", "stlplus3", "cmdLine", "histogram", "htmlDoc"]
        if self.version == "2.0":
            keep.append("vectorGraphics")
        for p in Path("src/third_party").iterdir():
            if p.is_dir() and p.name not in keep:
                rmdir(self, p)
        save(self, "src/third_party/CMakeLists.txt", textwrap.dedent("""\
            set(FAST_INCLUDE_INSTALL_DIR include/openMVG/third_party/fast)
            add_subdirectory(fast)
            set(STLPLUS_INCLUDE_INSTALL_DIR include/openMVG/third_party/stlplus3)
            set(STLPLUS_LIBRARY openMVG_stlplus PARENT_SCOPE)
            add_subdirectory(stlplus3)
            foreach(inDirectory cmdLine histogram htmlDoc vectorGraphics)
              install(DIRECTORY ${inDirectory} DESTINATION include/openMVG/third_party/ FILES_MATCHING PATTERN "*.hpp" PATTERN "*.h")
            endforeach()
        """))
        replace_in_file(self, "src/openMVG/exif/exif_IO_EasyExif.cpp", "third_party/", "")
        replace_in_file(self, "src/openMVG/exif/CMakeLists.txt", "openMVG_easyexif", "easyexif::easyexif")
        replace_in_file(self, "src/openMVG/matching/metric_hnsw.hpp", "third_party/", "")
        replace_in_file(self, "src/openMVG/matching/matcher_hnsw.hpp", "third_party/", "")
        if Version(self.version) >= "2.1":
            replace_in_file(self, "src/openMVG/multiview/LiGT/LiGT_algorithm.cpp", "third_party/spectra/include/Spectra", "Spectra")
        rmdir(self, "src/nonFree/sift/vl")
        save(self, "src/nonFree/sift/CMakeLists.txt", textwrap.dedent("""\
            install(
              FILES SIFT_describer.hpp SIFT_describer_io.hpp
              DESTINATION include/openMVG_dependencies/nonFree/sift
              COMPONENT headers
            )
        """))
        replace_in_file(self, "src/nonFree/sift/SIFT_describer.hpp", "nonFree/sift/vl/sift.h", "vl/sift.h")
        # Bypass a check for submodules
        mkdir(self, "src/dependencies/cereal/include")
        # Ensure internal dependencies are not used by accident
        replace_in_file(self, "src/CMakeLists.txt", "set(OpenMVG_USE_INTERNAL_", "# set(OpenMVG_USE_INTERNAL_")
        replace_in_file(self, "src/CMakeLists.txt", "find_package(OpenMP)", "find_package(OpenMP REQUIRED)")
        # Eigen v5 compatibility
        replace_in_file(self, "src/openMVG/numeric/eigen_alias_definition.hpp",
                        "#include <initializer_list>",
                        "#include <cassert>\n#include <initializer_list>")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_PROJECT_openMVG_INCLUDE"] = "conan_deps.cmake"
        tc.variables["OpenMVG_BUILD_SHARED"] = self.options.shared
        tc.variables["OpenMVG_BUILD_TESTS"] = False
        tc.variables["OpenMVG_BUILD_DOC"] = False
        tc.variables["OpenMVG_BUILD_EXAMPLES"] = False
        tc.variables["OpenMVG_BUILD_OPENGL_EXAMPLES"] = False
        tc.variables["OpenMVG_BUILD_SOFTWARES"] = self.options.programs
        tc.variables["OpenMVG_BUILD_GUI_SOFTWARES"] = False
        tc.variables["OpenMVG_BUILD_COVERAGE"] = False
        tc.variables["OpenMVG_USE_LIGT"] = self.options.enable_ligt
        tc.variables["OpenMVG_USE_OPENMP"] = self.options.with_openmp
        tc.variables["OpenMVG_USE_OPENCV"] = False
        tc.variables["OpenMVG_USE_OCVSIFT"] = False
        tc.variables["OpenMVG_USE_SPECTRA"] = Version(self.version) >= "2.1"

        # https://github.com/openMVG/openMVG/blob/v2.1/src/cmakeFindModules/OptimizeForArchitecture.cmake
        tc.variables["TARGET_ARCHITECTURE"] = self.options.get_safe("cpu_architecture", "none")
        tc.variables["USE_AVX"] = self.options.get_safe("avx", False) in ["avx", "avx2"]
        tc.variables["USE_AVX2"] = self.options.get_safe("avx", False) == "avx2"

        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0177"] = "NEW"

        if self.settings.os == "Windows":
            tc.preprocessor_definitions["NOMINMAX"] = None
            # Fix a missing /bigobj flag for 'matching' and 'multiview' components
            # and add the equivalent for MinGW as well
            if is_msvc(self):
                tc.extra_cflags.append("/bigobj")
                tc.extra_cxxflags.append("/bigobj")
            elif self.settings.compiler == "gcc":
                tc.extra_cflags.append("-Wa,-mbig-obj")
                tc.extra_cxxflags.append("-Wa,-mbig-obj")

        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("cereal", "cmake_file_name", "cereal")
        deps.set_property("ceres-solver", "cmake_file_name", "Ceres")
        deps.set_property("coin-clp", "cmake_file_name", "Clp")
        deps.set_property("coin-lemon", "cmake_file_name", "Lemon")
        deps.set_property("coin-osi", "cmake_file_name", "Osi")
        deps.set_property("coin-utils", "cmake_file_name", "CoinUtils")
        deps.set_property("flann", "cmake_file_name", "Flann")
        deps.set_property("flann::flann_c", "cmake_target_name", "flann::flann")
        deps.set_property("flann::flann_cpp", "cmake_target_name", "flann::flann_cpp")
        deps.set_property("libtiff", "cmake_file_name", "TIFF")
        deps.set_property("vlfeat", "cmake_target_name", "vlsift")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="src")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        for dll_file in glob.glob(os.path.join(self.package_folder, "lib", "*.dll")):
            rename(self, dll_file, os.path.join(self.package_folder, "bin", os.path.basename(dll_file)))
        rm(self, "*.cmake", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "openMVG", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share", "cmake"))

    @property
    def _openmvg_components(self):
        def pthread():
            if self.settings.os in ["Linux", "FreeBSD"]:
                return ["pthread"]
            return []

        def spectra():
            if Version(self.version) >= "2.1":
                return ["spectra::spectra"]
            return []

        return {
            "openmvg_camera": {
                "target": "openMVG_camera",
                "requires": ["openmvg_numeric", "cereal::cereal"],
            },
            "openmvg_exif": {
                "target": "openMVG_exif",
                "libs": ["openMVG_exif"],
                "requires": ["openmvg_easyexif"],
            },
            "openmvg_easyexif": {
                "target": "openMVG_easyexif",
                "requires": ["easyexif::easyexif"],
            },
            "openmvg_features": {
                "target": "openMVG_features",
                "libs": ["openMVG_features"],
                "requires": ["openmvg_fast", "openmvg_stlplus", "eigen::eigen", "cereal::cereal"],
                "add_library_name_prefix_to_include_dirs": True,
            },
            "openmvg_geodesy": {
                "target": "openMVG_geodesy",
                "requires": ["openmvg_numeric"],
            },
            "openmvg_geometry": {
                "target": "openMVG_geometry",
                "libs": ["openMVG_geometry"],
                "requires": ["openmvg_numeric", "openmvg_linearprogramming", "cereal::cereal"],
            },
            "openmvg_graph": {
                "target": "openMVG_graph",
                "requires": ["coin-lemon::coin-lemon"],
            },
            "openmvg_image": {
                "target": "openMVG_image",
                "libs": ["openMVG_image"],
                "requires": ["openmvg_numeric", "libpng::libpng", "libtiff::tiff", "libjpeg-meta::jpeg"],
            },
            "openmvg_linearprogramming": {
                "target": "openMVG_linearProgramming",
                "libs": ["openMVG_linearProgramming"],
                "requires": ["openmvg_numeric", "coin-clp::coin-clp", "coin-osi::coin-osi", "coin-utils::coin-utils"],
            },
            "openmvg_linftycomputervision": {
                "target": "openMVG_lInftyComputerVision",
                "libs": ["openMVG_lInftyComputerVision"],
                "requires": ["openmvg_linearprogramming", "openmvg_multiview"],
            },
            "openmvg_matching": {
                "target": "openMVG_matching",
                "libs": ["openMVG_matching"],
                "requires": ["openmvg_features", "openmvg_stlplus", "cereal::cereal", "flann::flann", "hnswlib::hnswlib"],
                "system_libs": pthread(),
                "add_library_name_prefix_to_include_dirs": True,
            },
            "openmvg_kvld": {
                "target": "openMVG_kvld",
                "libs": ["openMVG_kvld"],
                "requires": ["openmvg_features", "openmvg_image"],
            },
            "openmvg_matching_image_collection": {
                "target": "openMVG_matching_image_collection",
                "libs": ["openMVG_matching_image_collection"],
                "requires": ["openmvg_matching", "openmvg_multiview"],
                "add_library_name_prefix_to_include_dirs": True,
            },
            "openmvg_multiview": {
                "target": "openMVG_multiview",
                "libs": ["openMVG_multiview"],
                "requires": ["openmvg_numeric", "openmvg_system", "openmvg_graph", "ceres-solver::ceres-solver"] + spectra(),
            },
            "openmvg_numeric": {
                "target": "openMVG_numeric",
                "libs": ["openMVG_numeric"],
                "requires": ["eigen::eigen"],
                "defines": [(is_msvc(self), ["_USE_MATH_DEFINES"])],
            },
            "openmvg_robust_estimation": {
                "target": "openMVG_robust_estimation",
                "libs": ["openMVG_robust_estimation"],
                "requires": ["openmvg_numeric"],
                "add_library_name_prefix_to_include_dirs": True,
            },
            "openmvg_sfm": {
                "target": "openMVG_sfm",
                "libs": ["openMVG_sfm"],
                "requires": [
                    "openmvg_geometry", "openmvg_features", "openmvg_graph", "openmvg_matching",
                    "openmvg_multiview", "openmvg_image", "openmvg_linftycomputervision",
                    "openmvg_system", "openmvg_stlplus", "cereal::cereal", "ceres-solver::ceres-solver",
                ],
                "add_library_name_prefix_to_include_dirs": True,
            },
            "openmvg_system": {
                "target": "openMVG_system",
                "libs": ["openMVG_system"],
            },
            "openmvg_fast": {
                "target": "openMVG_fast",
                "libs": ["openMVG_fast"],
            },
            "openmvg_stlplus": {
                "target": "openMVG_stlplus",
                "libs": ["openMVG_stlplus"],
            },
            "openmvg_svg": {
                "target": "openMVG_svg",
            },
            "openmvg_vlsift": {
                "target": "vlsift",
                "requires": ["openmvg_features", "openmvg_image", "vlfeat::vlfeat"],
            },
        }

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenMVG")

        for component, values in self._openmvg_components.items():
            target = values["target"]
            libs = values.get("libs", [])
            defines = []
            for _condition, _defines in values.get("defines", []):
                if _condition:
                    defines.extend(_defines)

            self.cpp_info.components[component].set_property("cmake_target_name", f"OpenMVG::{target}")
            if libs:
                self.cpp_info.components[component].libs = libs
            self.cpp_info.components[component].includedirs.append("include/openMVG_dependencies")
            if values.get("add_library_name_prefix_to_include_dirs"):
                self.cpp_info.components[component].includedirs.append("include/openMVG")
            self.cpp_info.components[component].defines = defines
            self.cpp_info.components[component].requires = values.get("requires", [])
            self.cpp_info.components[component].system_libs = values.get("system_libs", [])
            self.cpp_info.components[component].resdirs = ["lib/openMVG" if Version(self.version) >= "2.1" else  "share/openMVG"]

        if self.options.with_openmp:
            for component_name in [
                "camera", "features", "image", "matching", "kvld", "matching_image_collection",
                "multiview", "robust_estimation", "sfm", "vlsift",
            ]:
                self.cpp_info.components[f"openmvg_{component_name}"].requires.append("openmp::openmp")
