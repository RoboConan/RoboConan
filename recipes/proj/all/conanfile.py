import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.26"


class ProjConan(ConanFile):
    name = "proj"
    description = "Cartographic Projections and Coordinate Transformations Library."
    license = "MIT"
    homepage = "https://proj.org"
    topics = ("dsp", "proj", "proj4", "projections", "gis", "geospatial")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tiff": [True, False],
        "with_curl": [True, False],
        "build_executables": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tiff": True,
        "with_curl": True,
        "build_executables": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("nlohmann_json/[^3]")
        self.requires("sqlite3/[>=3.44 <4]")
        if self.options.with_tiff:
            self.requires("libtiff/[>=4.5 <5]")
        if self.options.with_curl:
            self.requires("libcurl/[>=7.78.0 <9]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22.1 <5]")
        self.tool_requires("sqlite3/<host_version>")

    def validate(self):
        if Version(self.version) >= "9.6.0":
            # https://github.com/OSGeo/PROJ/blob/9.6.0/CMakeLists.txt#L24-L27
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_CCT"] = self.options.build_executables
        tc.cache_variables["BUILD_CS2CS"] = self.options.build_executables
        tc.cache_variables["BUILD_GEOD"] = self.options.build_executables
        tc.cache_variables["BUILD_GIE"] = self.options.build_executables
        tc.cache_variables["BUILD_PROJ"] = self.options.build_executables
        tc.cache_variables["BUILD_PROJINFO"] = self.options.build_executables
        tc.cache_variables["ENABLE_TIFF"] = self.options.with_tiff
        tc.cache_variables["ENABLE_CURL"] = self.options.with_curl
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["ENABLE_IPO"] = False
        tc.cache_variables["BUILD_PROJSYNC"] = self.options.build_executables and self.options.with_curl
        tc.cache_variables["NLOHMANN_JSON_ORIGIN"] = "external"
        tc.cache_variables["CMAKE_MACOSX_BUNDLE"] = False
        if self.settings.os == "Linux":
            # Workaround for: https://github.com/conan-io/conan/issues/13560
            tc.add_rpath_link = True
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.with_tiff:
            # PROJ consumes CMake's FindTIFF target rather than libtiff's config target.
            deps.set_property("libtiff", "cmake_find_mode", "module")
        deps.generate()

    def _patch_sources(self):
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")

        replace_in_file(self, cmakelists, "/W4", "")

        # Aggressive workaround against SIP on macOS, to handle sqlite3 executable
        # linked to shared sqlite3 lib
        if is_apple_os(self):
            cmake_sqlite_call = "generate_proj_db.cmake"
            pattern = '"${EXE_SQLITE3}"'
            lib_paths = self.dependencies.build["sqlite3"].cpp_info.libdirs
            replace_in_file(self,
                os.path.join(self.source_folder, "data", cmake_sqlite_call),
                f"COMMAND {pattern}",
                f'COMMAND ${{CMAKE_COMMAND}} -E env "DYLD_LIBRARY_PATH={":".join(lib_paths)}" {pattern}'
            )

        # Remove warning flags that are unfamiliar to GCC 5
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "8.0":
            replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"), "${PROJ_C_WARN_FLAGS}", "")
            replace_in_file(self, os.path.join(self.source_folder, "src", "CMakeLists.txt"), "${PROJ_CXX_WARN_FLAGS}", "")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "share", "bash-completion"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "proj")
        self.cpp_info.set_property("cmake_target_name", "PROJ::proj")
        self.cpp_info.set_property("pkg_config_name", "proj")
        self.cpp_info.components["projlib"].set_property("cmake_target_name", "PROJ::proj")
        self.cpp_info.components["projlib"].set_property("pkg_config_name", "proj")

        self.cpp_info.components["projlib"].libs = collect_libs(self)
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["projlib"].system_libs.append("m")
            self.cpp_info.components["projlib"].system_libs.append("pthread")
        if self.settings.os == "Linux":
            self.cpp_info.components["projlib"].system_libs.append("dl")
        if self.settings.os == "Windows":
            self.cpp_info.components["projlib"].system_libs.extend(["shell32", "ole32"])
        if not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.components["projlib"].system_libs.append(libcxx)
        self.cpp_info.components["projlib"].requires.extend(["nlohmann_json::nlohmann_json", "sqlite3::sqlite3"])
        if self.options.with_tiff:
            self.cpp_info.components["projlib"].requires.append("libtiff::tiff")
        if self.options.with_curl:
            self.cpp_info.components["projlib"].requires.append("libcurl::libcurl")
        if not self.options.shared:
            self.cpp_info.components["projlib"].defines.append("PROJ_DLL=")

        # see https://proj.org/usage/environmentvars.html#envvar-PROJ_DATA
        res_path = os.path.join(self.package_folder, "share", "proj")
        self.runenv_info.prepend_path("PROJ_DATA", res_path)
        if self.options.build_executables:
            self.buildenv_info.prepend_path("PROJ_DATA", res_path)
