import os
import textwrap

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import check_min_vs

required_conan_version = ">=2.1"


class CorradeConan(ConanFile):
    name = "corrade"
    description = "Corrade is a multiplatform utility library written in C++11/C++14."
    license = "MIT"
    homepage = "https://magnum.graphics/corrade"
    topics = ("magnum", "filesystem", "console", "environment", "os")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_deprecated": [True, False],
        "build_multithreaded": [True, False],
        "build_static_unique_globals": [True, False, "auto"],
        "static_unique_globals_dll_name": [None, "ANY"],
        "testsuite_target_xctest": [True, False],
        "with_interconnect": [True, False],
        "with_pluginmanager": [True, False],
        "with_testsuite": [True, False],
        "with_utility": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_deprecated": True,
        "build_multithreaded": True,
        "build_static_unique_globals": "auto",
        "static_unique_globals_dll_name": None,
        "testsuite_target_xctest": False,
        "with_interconnect": True,
        "with_pluginmanager": True,
        "with_testsuite": True,
        "with_utility": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def config_options(self):
        if self.settings.os != "Windows":
            self.options.rm_safe("static_unique_globals_dll_name")
        if not is_apple_os(self):
            self.options.rm_safe("testsuite_target_xctest")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("build_static_unique_globals")
            self.options.rm_safe("static_unique_globals_dll_name")
        elif not self.options.build_static_unique_globals:
            self.options.rm_safe("static_unique_globals_dll_name")
        if self.options.get_safe("testsuite_target_xctest"):
            self.options.with_testsuite.value = True
        if self.options.with_testsuite or self.options.with_interconnect or self.options.with_pluginmanager:
            self.options.with_utility.value = True

    def validate(self):
        check_min_vs(self, 190)
        if self.options.with_interconnect and not self.options.build_deprecated:
            raise ConanInvalidConfiguration("Component 'interconnect' requires 'build_deprecated=True'")

    def build_requirements(self):
        if not can_run(self):
            self.tool_requires(f"corrade/{self.version}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CORRADE_BUILD_STATIC"] = not self.options.shared
        tc.variables["CORRADE_BUILD_STATIC_PIC"] = self.options.get_safe("fPIC", False)
        tc.variables["CORRADE_BUILD_DEPRECATED"] = self.options.build_deprecated
        tc.variables["CORRADE_BUILD_MULTITHREADED"] = self.options.build_multithreaded
        build_static_unique_globals = self.options.get_safe("build_static_unique_globals", "auto")
        if build_static_unique_globals != "auto":
            tc.variables["CORRADE_BUILD_STATIC_UNIQUE_GLOBALS"] = build_static_unique_globals
        if self.options.get_safe("static_unique_globals_dll_name"):
            tc.variables["CORRADE_BUILD_STATIC_UNIQUE_GLOBALS_DLL_NAME"] = self.options.static_unique_globals_dll_name
        tc.variables["CORRADE_WITH_INTERCONNECT"] = self.options.with_interconnect
        tc.variables["CORRADE_WITH_MAIN"] = True
        tc.variables["CORRADE_WITH_PLUGINMANAGER"] = self.options.with_pluginmanager
        tc.variables["CORRADE_WITH_TESTSUITE"] = self.options.with_testsuite
        tc.variables["CORRADE_WITH_UTILITY"] = self.options.with_utility
        tc.variables["CORRADE_WITH_RC"] = True
        tc.variables["CORRADE_TESTSUITE_TARGET_XCTEST"] = self.options.get_safe("testsuite_target_xctest", False)
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _extract_cmake_shim(self) -> str:
        find_corrade = load(self, os.path.join(
            self.package_folder, "share", "cmake", "Corrade", "FindCorrade.cmake"))
        flags_begin = find_corrade.find("# Read flags from configuration")
        flags_end = find_corrade.find("# CMake module dir", flags_begin)
        if flags_begin == -1 or flags_end == -1:
            raise ConanException("Unable to extract configuration variables from FindCorrade.cmake")
        configure_flags = find_corrade[flags_begin:flags_end]
        shim = textwrap.dedent("""\
            # Generated from the packaged FindCorrade.cmake configuration-variable block.
            set(_CORRADE_CONFIGURE_FILE
                "${CMAKE_CURRENT_LIST_DIR}/../../../include/Corrade/configure.h")
            """) + configure_flags + textwrap.dedent("""\
            set(_CORRADE_MODULE_DIR
                "${CMAKE_CURRENT_LIST_DIR}/../../cmake/Corrade")
            set(CORRADE_USE_MODULE "${_CORRADE_MODULE_DIR}/UseCorrade.cmake")
            if(CORRADE_TARGET_EMSCRIPTEN)
                set(CORRADE_DEPENDENCY_MODULE_DIR "${_CORRADE_MODULE_DIR}/dependencies")
            endif()
            if(CORRADE_BUILD_DEPRECATED)
                set(CORRADE_LIB_SUFFIX_MODULE "${_CORRADE_MODULE_DIR}/CorradeLibSuffix.cmake")
            endif()

            if(NOT TARGET Corrade::rc)
                find_program(CORRADE_RC_PROGRAM NAMES corrade-rc PATHS ENV PATH NO_DEFAULT_PATH)
                get_filename_component(CORRADE_RC_PROGRAM "${CORRADE_RC_PROGRAM}" ABSOLUTE)
                set(CORRADE_RC_EXECUTABLE ${CORRADE_RC_PROGRAM} CACHE FILEPATH
                    "The corrade-rc resource compiler")
                add_executable(Corrade::rc IMPORTED)
                set_property(TARGET Corrade::rc PROPERTY IMPORTED_LOCATION
                    ${CORRADE_RC_EXECUTABLE})
            endif()
        """)
        return shim

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        shim = self._extract_cmake_shim()
        save(self, os.path.join(self.package_folder, "share", "conan", "corrade", "conan-corrade-vars.cmake"), shim)
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "Corrade")

        suffix = "-d" if self.settings.build_type == "Debug" else ""

        containers = self.cpp_info.components["containers"]
        containers.set_property("cmake_target_name", "Corrade::Containers")

        main = self.cpp_info.components["main"]
        main.set_property("cmake_target_name", "Corrade::Main")
        if self.settings.compiler == "msvc":
            main.libs = ["CorradeMain" + suffix]

        if self.options.with_utility:
            utility = self.cpp_info.components["utility"]
            utility.set_property("cmake_target_name", "Corrade::Utility")
            utility.libs = ["CorradeUtility" + suffix]
            utility.requires = ["containers"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                utility.system_libs = ["m", "dl"]

        if self.options.with_interconnect:
            interconnect = self.cpp_info.components["interconnect"]
            interconnect.set_property("cmake_target_name", "Corrade::Interconnect")
            interconnect.libs = ["CorradeInterconnect" + suffix]
            interconnect.requires = ["containers", "utility"]

        if self.options.with_pluginmanager:
            plugin_manager = self.cpp_info.components["plugin_manager"]
            plugin_manager.set_property("cmake_target_name", "Corrade::PluginManager")
            plugin_manager.libs = ["CorradePluginManager" + suffix]
            plugin_manager.requires = ["containers", "utility"]

        if self.options.with_testsuite:
            test_suite = self.cpp_info.components["test_suite"]
            test_suite.set_property("cmake_target_name", "Corrade::TestSuite")
            test_suite.libs = ["CorradeTestSuite" + suffix]
            test_suite.requires = ["containers", "utility", "main"]

        self.cpp_info.set_property("cmake_build_modules", [
            "share/conan/corrade/conan-corrade-vars.cmake",
            "share/cmake/Corrade/UseCorrade.cmake",
        ])
