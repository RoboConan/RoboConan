import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class MetavisionSdkConan(ConanFile):
    name = "metavision-sdk"
    description = "Open source SDK to create applications leveraging event-based vision hardware equipment"
    license = "Apache"
    homepage = "https://github.com/prophesee-ai/openeb"
    topics = ("sdk", "computer-vision", "camera-api", "neuromorphic", "event-camera")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_hdf5": [True, False],
        # modules
        "stream": [True, False],
        "ui": [True, False],
        # Advanced SDK options
        "advanced_sdk_repo_url": [None, "ANY"],
        "ubuntu_version": ["ANY"],
    }
    default_options = {
        "with_hdf5": True,
        # modules
        "stream": True,
        "ui": True,
        # Advanced SDK options
        "advanced_sdk_repo_url": None,
        "ubuntu_version": "jammy",

        "boost/*:with_filesystem": True,
        "boost/*:with_program_options": True,
        "boost/*:with_timer": True,
    }

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    @property
    def _stream_module(self):
        return "stream" if Version(self.version).major >= 5 else "driver"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Android":
            del self.options.with_hdf5

    def configure(self):
        if not self.options.stream:
            self.options.rm_safe("with_hdf5")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # metavision/psee_hw_layer/boards/utils/psee_libusb.h
        self.requires("libusb/[^1.0.26]", transitive_headers=True)
        # several headers, e.g. metavision/sdk/core/preprocessors/json_parser.h
        self.requires("boost/[^1.71.0]", transitive_headers=True)
        # OpenCV is used in many public headers
        opencv_extra = {"videoio": True}
        if self.options.advanced_sdk_repo_url:
            opencv_extra.update({"highgui": True, "objdetect": True})
        self.requires("opencv/[^4.5]", transitive_headers=True, options=opencv_extra)
        if self.options.stream:
            # newer version conflicts with opencv
            self.requires("protobuf/[>=3.21.12]")
            if self.options.get_safe("with_hdf5"):
                # hdf5_ecf/ecf_h5filter.h
                self.requires("hdf5/[^1.8]", transitive_headers=True)
        if self.options.ui:
            # metavision/sdk/ui/utils/opengl_api.h
            self.requires("opengl/system", transitive_headers=True)
            self.requires("glew/2.2.0", transitive_headers=True)
            self.requires("glfw/[^3.4]", transitive_headers=True)

        if self.options.advanced_sdk_repo_url:
            self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
            # self.requires("boost/[^1.71.0]", force=True)
            # self.requires("opencv/4.5.5", force=True)
            # self.requires("protobuf/3.12.4", force=True)

    def validate(self):
        if self.options.advanced_sdk_repo_url and not self.conan_data["advanced-sdk"].get(self.version):
            raise ConanInvalidConfiguration(f"This recipe does not support the advanced SDK for version {self.version}")
        check_min_cppstd(self, 17)

    def build_requirements(self):
        if self.options.stream:
            self.tool_requires("protobuf/<host_version>")
        if self.options.advanced_sdk_repo_url:
            self.build_requires("patchelf/[*]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["openeb"], strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["hdf5_ecf"], strip_root=True,
            destination=os.path.join("sdk", "modules", self._stream_module, "cpp", "3rdparty", "hdf5_ecf"))
        apply_conandata_patches(self)
        # Let Conan set the C++ version
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        # Unvendor nlohmann_json
        rmdir(self, os.path.join("utils", "cpp", "3rdparty"))
        # Ensure Conan deps are used
        rmdir(self, os.path.join("cmake", "Modules"))
        # Don't look for nvcc - only used for Python bindings
        replace_in_file(self, "CMakeLists.txt", "check_language(CUDA)", "")
        # Only used for Python bindings
        rmdir(self, os.path.join("sdk", "modules", "core_ml", "models"))

    @property
    def _enabled_modules(self):
        modules = ["base", "core"]
        if self.options.stream:
            modules.append(self._stream_module)
        if self.options.ui:
            modules.append("ui")
        return modules

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["BUILD_SAMPLES"] = False
        tc.cache_variables["GENERATE_DOC"] = False
        tc.cache_variables["COMPILE_PYTHON3_BINDINGS"] = False
        tc.cache_variables["UDEV_RULES_SYSTEM_INSTALL"] = False
        tc.cache_variables["HDF5_DISABLED"] = not self.options.get_safe("with_hdf5", False)
        tc.cache_variables["METAVISION_SELECTED_MODULES"] = ";".join(self._enabled_modules)
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("libusb", "cmake_target_name", "libusb-1.0")
        deps.generate()

    def _download_advanced_sdk(self):
        base_url = str(self.options.advanced_sdk_repo_url).split("ubuntu")[0]
        base_url += f"ubuntu/dists/{self.options.ubuntu_version}/sdk/binary-amd64/"
        for pkg_info in self.conan_data["advanced-sdk"][self.version]:
            filename = pkg_info["filename"]
            download(self, base_url + filename, filename, sha256=pkg_info["sha256"])
            self._extract_deb(filename, os.path.join(self.build_folder, "advanced-sdk"))

    def _extract_deb(self, deb_file, dst):
        self._utils.extract_deb(deb_file, dst)

    def build(self):
        if self.options.advanced_sdk_repo_url:
            self._download_advanced_sdk()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _fix_opencv_dep_soname(self):
        # Use patchelf to replace opencv v4.5d dynamic dependencies with v4.5.x in the advanced SDK binaries.
        # 4.5d is a soname used by Ubuntu only.
        opencv_version = self.dependencies["opencv"].ref.version
        replacements = [
            f"--replace-needed libopencv_{mod}.so.4.5d libopencv_{mod}.so.{opencv_version}"
            for mod in ["calib3d", "core", "imgproc", "videoio"]
        ]
        for lib in Path(self.package_folder, "lib").rglob("*.so"):
            self.run(f"patchelf {' '.join(replacements)} {lib}")

    def package(self):
        if self.options.advanced_sdk_repo_url:
            copy(self, "*", os.path.join(self.build_folder, "advanced-sdk", "usr"), self.package_folder, keep_path=True)
            self._fix_opencv_dep_soname()
            copy(self, "LICENSE_METAVISION_SDK",
                 os.path.join(self.build_folder, "advanced-sdk", "usr", "share", "metavision", "licensing"),
                 os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE_OPEN",
             os.path.join(self.source_folder, "licensing"),
             os.path.join(self.package_folder, "licenses"))
        if self.options.stream:
            copy(self, "LICENSE",
                 os.path.join(self.source_folder, "sdk", "modules", self._stream_module, "cpp", "3rdparty", "hdf5_ecf"),
                 os.path.join(self.package_folder, "licenses", "hdf5_ecf"))
        cmake = CMake(self)
        cmake.install()
        if self.options.advanced_sdk_repo_url:
            copy(self, "*/libmetavision_psee_hw_layer.so", os.path.join(self.build_folder, "advanced-sdk", "usr"), self.package_folder, keep_path=True)
        rmdir(self, os.path.join(self.package_folder, "share", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share", "hdf5_ecf"))
        rmdir(self, os.path.join(self.package_folder, "share", "metavision", "hal_psee_plugins"))
        rmdir(self, os.path.join(self.package_folder, "share", "metavision", "licensing"))
        rmdir(self, os.path.join(self.package_folder, "share", "metavision", "log"))

    def package_info(self):
        # The project also installs config files for MetavisionHAL, MetavisionPSEEHWLayer and hdf5_ecf,
        # which cannot be reproduced by Conan
        self.cpp_info.set_property("cmake_file_name", "MetavisionSDK")

        self.cpp_info.components["HAL"].set_property("cmake_target_name", "Metavision::HAL")
        self.cpp_info.components["HAL"].libs = ["metavision_hal"]
        self.cpp_info.components["HAL"].requires = ["base"]
        self.cpp_info.components["HAL"].resdirs = [os.path.join("share", "HAL", "resources")]
        self.runenv_info.append("MV_HAL_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "metavision", "hal", "plugins"))

        self.cpp_info.components["HAL_discovery"].set_property("cmake_target_name", "Metavision::HAL_discovery")
        self.cpp_info.components["HAL_discovery"].libs = ["metavision_hal_discovery"]
        self.cpp_info.components["HAL_discovery"].requires = ["HAL"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["HAL_discovery"].system_libs.append("dl")

        self.cpp_info.components["PSEEHWLayer"].set_property("cmake_target_name", "Metavision::PSEEHWLayer")
        self.cpp_info.components["PSEEHWLayer"].libs = ["metavision_psee_hw_layer"]
        self.cpp_info.components["PSEEHWLayer"].libdirs = [os.path.join("lib", "metavision", "hal", "plugins")]
        self.cpp_info.components["PSEEHWLayer"].requires = [
            "HAL",
            "libusb::libusb",
        ]

        self.cpp_info.components["base"].set_property("cmake_target_name", "MetavisionSDK::base")
        self.cpp_info.components["base"].libs = ["metavision_sdk_base"]

        self.cpp_info.components["core"].set_property("cmake_target_name", "MetavisionSDK::core")
        self.cpp_info.components["core"].libs = ["metavision_sdk_core"]
        self.cpp_info.components["core"].requires = [
            "base",
            "opencv::opencv_core",
            "opencv::opencv_imgproc",
            "opencv::opencv_videoio",
            "boost::headers",
            "boost::timer",
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["core"].system_libs.append("m")

        if self.options.stream:
            self.cpp_info.components["hdf5_ecf_codec"].set_property("cmake_target_name", "hdf5_ecf_codec")
            self.cpp_info.components["hdf5_ecf_codec"].libs = ["hdf5_ecf_codec"]
            self.runenv_info.append("HDF5_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "hdf5", "plugin"))

            self.cpp_info.components[self._stream_module].set_property("cmake_target_name", f"MetavisionSDK::{self._stream_module}")
            if Version(self.version) < "5.0":
                self.cpp_info.components[self._stream_module].set_property("cmake_target_aliases", ["MetavisionSDK::stream"])
            self.cpp_info.components[self._stream_module].libs = [f"metavision_sdk_{self._stream_module}"]
            self.cpp_info.components[self._stream_module].requires = [
                "base",
                "core",
                "HAL",
                "HAL_discovery",
                "protobuf::libprotobuf",
                "hdf5_ecf_codec",
            ]
            if self.options.get_safe("with_hdf5"):
                self.cpp_info.components["stream"].requires.append("hdf5::hdf5_cpp")

        if self.options.ui:
            self.cpp_info.components["ui"].set_property("cmake_target_name", "MetavisionSDK::ui")
            self.cpp_info.components["ui"].libs = ["metavision_sdk_ui"]
            self.cpp_info.components["ui"].requires = [
                "core",
                "opencv::opencv_core",
                "opengl::opengl",
                "glfw::glfw",
                "glew::glew",
            ]

        if self.options.advanced_sdk_repo_url:
            self.cpp_info.components["analytics"].set_property("cmake_target_name", "MetavisionSDK::analytics")
            self.cpp_info.components["analytics"].libs = ["metavision_sdk_analytics"]
            self.cpp_info.components["analytics"].requires = [
                "cv",
                "boost::filesystem",
                "opencv::opencv_videoio",
                "opencv::opencv_highgui",
            ]

            self.cpp_info.components["calibration"].set_property("cmake_target_name", "MetavisionSDK::calibration")
            self.cpp_info.components["calibration"].libs = ["metavision_sdk_calibration"]
            self.cpp_info.components["calibration"].requires = [
                "cv",
                "opencv::opencv_calib3d",
            ]

            self.cpp_info.components["cv"].set_property("cmake_target_name", "MetavisionSDK::cv")
            self.cpp_info.components["cv"].libs = ["metavision_sdk_cv"]
            self.cpp_info.components["cv"].requires = [
                "base",
                "core",
                "opencv::opencv_imgproc",
                "opencv::opencv_core",
                "eigen::eigen",
            ]

            self.cpp_info.components["cv3d"].set_property("cmake_target_name", "MetavisionSDK::cv3d")
            self.cpp_info.components["cv3d"].libs = ["metavision_sdk_cv3d"]
            self.cpp_info.components["cv3d"].requires = [
                "cv",
                "opencv::opencv_calib3d",
                "eigen::eigen",
            ]

            # Header-only component
            self.cpp_info.components["ml"].set_property("cmake_target_name", "MetavisionSDK::ml")
            self.cpp_info.components["ml"].requires = [
                "base",
                "core",
                "cv",
                self._stream_module,
                "opencv::opencv_objdetect",
                "opencv::opencv_highgui",
                # libtorch
            ]
