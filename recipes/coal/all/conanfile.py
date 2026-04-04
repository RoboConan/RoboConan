import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class CoalConan(ConanFile):
    name = "coal"
    description = "An extension of the Flexible Collision Library. Formerly known as HPP-FCL."
    license = "BSD-3-Clause"
    homepage = "https://github.com/coal-library/coal"
    topics = ("collision-detection", "robotics")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "hpp_fcl_compatibility": [True, False],
        "enable_logging": [True, False],
        "with_octomap": [True, False],
        "with_qhull": [True, False],
        # Python bindings
        "python_bindings": [True, False],
        "generate_python_stubs": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "hpp_fcl_compatibility": False,
        "enable_logging": False,
        "with_octomap": True,
        "with_qhull": False,

        # Python bindings
        "python_bindings": False,
        "generate_python_stubs": True,

        "boost/*:with_chrono": True,
        "boost/*:with_thread": True,
        "boost/*:with_date_time": True,
        "boost/*:with_filesystem": True,
        "boost/*:with_serialization": True,
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.python_bindings:
            del self.options.generate_python_stubs
        else:
            self.options["boost"].with_python = True
        if self.options.enable_logging:
            self.options["boost"].with_log = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        self.requires("boost/[^1.71.0]", transitive_headers=True, transitive_libs=True)
        self.requires("assimp/[^5.1.6]")
        if self.options.with_octomap:
            self.requires("octomap/[^1.6]", transitive_headers=True, transitive_libs=True)
        if self.options.with_qhull:
            self.requires("qhull/[^8.1]")
        if self.options.python_bindings:
            # eigenpy adds cpython and numpy deps transitively
            self.requires("eigenpy/[^3.11.0]")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.options.with_qhull and self.dependencies["qhull"].options.shared:
            raise ConanInvalidConfiguration("-o qhull/*:shared=False is required for Qhull::qhullcpp component")

    def build_requirements(self):
        self.tool_requires("jrl-cmakemodules/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.python_bindings:
            self.tool_requires("eigenpy/[^3.11.0]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # latest jrl-cmakemodules requires CMake 3.22 or greater
        replace_in_file(self, "CMakeLists.txt",
                        "cmake_minimum_required(VERSION 3.10)",
                        "cmake_minimum_required(VERSION 3.22)")
        # get jrl-cmakemodules from Conan
        replace_in_file(self, "CMakeLists.txt", "set(JRL_CMAKE_MODULES ", " # set(JRL_CMAKE_MODULES ")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["COAL_BACKWARD_COMPATIBILITY_WITH_HPP_FCL"] = self.options.hpp_fcl_compatibility
        tc.cache_variables["COAL_HAS_QHULL"] = self.options.with_qhull
        tc.cache_variables["BUILD_PYTHON_INTERFACE"] = self.options.python_bindings
        tc.cache_variables["GENERATE_PYTHON_STUBS"] = self.options.get_safe("generate_python_stubs")
        tc.cache_variables["STUBGEN_MAIN_FILE"] = os.path.join(self.source_folder, "stubgen/pybind11_stubgen/__main__.py").replace("\\", "/")
        tc.cache_variables["JRL_CMAKE_MODULES"] = self.dependencies.build["jrl-cmakemodules"].cpp_info.builddirs[0].replace("\\", "/")
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        tc.cache_variables["BUILDING_ROS2_PACKAGE"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("qhull::libqhull_r", "cmake_target_name", "Qhull::qhull_r")
        deps.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        if self.options.get_safe("generate_python_stubs"):
            venv = self._utils.PythonVenv(self)
            venv.generate()
            # stubgen tries to load the built Python module
            if can_run(self):
                venv = VirtualRunEnv(self)
                venv.generate(scope="build")

    def build(self):
        if self.options.get_safe("generate_python_stubs"):
            self._utils.pip_install(self, ["scipy"])
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def _find_installed_site_packages(self):
        return str(next(Path(self.package_folder).rglob("__init__.py")).parent.parent)

    def package_info(self):
        # Also exports hpp-fclConfig.cmake if hpp_fcl_compatibility is True
        self.cpp_info.set_property("cmake_file_name", "coal")
        self.cpp_info.set_property("cmake_config_version_compat", "AnyNewerVersion")
        self.cpp_info.set_property("pkg_config_name", "_coal_aggregate")

        core = self.cpp_info.components["core"]
        core.set_property("cmake_target_name", "coal::coal")
        core.set_property("cmake_target_aliases", ["hpp-fcl::hpp-fcl"])
        core.set_property("pkg_config_name", "coal")
        core.set_property("pkg_config_aliases", ["hpp-fcl"])
        core.libs = ["coal"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            core.system_libs = ["m"]
        if self.settings.compiler == "msvc":
            core.cxxflags.append("/bigobj")
            core.defines.append("NOMINMAX")
        core.requires = [
            "eigen::eigen",
            "boost::chrono",
            "boost::filesystem",
            "boost::serialization",
            "assimp::assimp",
        ]
        if self.settings.os == "Windows":
            core.requires.extend(["boost::date_time", "boost::thread"])
        if self.options.enable_logging:
            core.requires.append("boost::log")
        if self.options.with_octomap:
            core.requires.append("octomap::octomap")
        if self.options.with_qhull:
            core.requires.append("qhull::qhull")
        if not self.options.shared:
            core.defines.append("COAL_STATIC")
        if self.options.hpp_fcl_compatibility:
            core.defines.append("COAL_BACKWARD_COMPATIBILITY_WITH_HPP_FCL")
        if self.options.with_octomap:
            octomap_version = self.dependencies["octomap"].ref.version
            core.defines.extend([
                "COAL_HAS_OCTOMAP",
                "COAL_HAVE_OCTOMAP",
                f"OCTOMAP_MAJOR_VERSION={octomap_version.major}",
                f"OCTOMAP_MINOR_VERSION={octomap_version.minor}",
                f"OCTOMAP_PATCH_VERSION={octomap_version.patch}",
            ])

        if self.options.python_bindings:
            pywrap = self.cpp_info.components["pywrap"]
            pywrap.set_property("cmake_target_name", "coal::coal_pywrap")
            pywrap.requires = ["core", "eigenpy::eigenpy"]
            self.runenv_info.prepend_path("PYTHONPATH", self._find_installed_site_packages())
