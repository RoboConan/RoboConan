import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OneTBBConan(ConanFile):
    name = "onetbb"
    license = "Apache-2.0"
    homepage = "https://github.com/uxlfoundation/oneTBB"
    description = (
        "oneAPI Threading Building Blocks (oneTBB) lets you easily write parallel C++"
        " programs that take full advantage of multicore performance, that are portable, composable"
        " and have future-proof scalability.")
    topics = ("tbb", "threading", "parallelism", "tbbmalloc")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "tbbmalloc": [True, False],
        "tbbproxy": [True, False],
        "tbbbind": [True, False],
        "interprocedural_optimization": [True, False],
        "build_apple_frameworks": [True, False],
    }
    default_options = {
        "tbbmalloc": True,
        "tbbproxy": True,
        "tbbbind": True,
        "interprocedural_optimization": True,
        "build_apple_frameworks": False,
    }

    @property
    def _tbbbind_explicit_hwloc(self):
        # during cross-compilation, oneTBB does not search for HWLOC and we need to specify it explicitly
        # but then oneTBB creates an imported SHARED target from provided paths, so we have to set shared=True
        return self.options.get_safe("tbbbind") and cross_building(self)

    def config_options(self):
        if is_apple_os(self) and self.settings.os != "Macos":
            del self.options.tbbbind
        if self.settings.os == "Android":
            del self.options.interprocedural_optimization
        if not is_apple_os(self):
            del self.options.build_apple_frameworks

    def configure(self):
        if self.options.tbbproxy:
            self.options.tbbmalloc.value = True
        if self._tbbbind_explicit_hwloc:
            self.options["hwloc"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.get_safe("tbbbind"):
            self.requires("hwloc/[^2.9.3]")

    def validate(self):
        if self.settings.compiler == "apple-clang" and Version(self.settings.compiler.version) < "11.0":
            raise ConanInvalidConfiguration(f"{self.ref} couldn't be built by apple-clang < 11.0")
        if self._tbbbind_explicit_hwloc and not self.dependencies["hwloc"].options.get_safe("shared", True):
            raise ConanInvalidConfiguration(f"{self.ref} requires hwloc:shared=True to be built.")

    def build_requirements(self):
        if self.options.get_safe("tbbbind") and not self._tbbbind_explicit_hwloc:
            if not self.conf.get("tools.gnu:pkg_config", check_type=str):
                self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TBB_TEST"] = False
        tc.variables["TBB_STRICT"] = False
        tc.variables["TBBMALLOC_BUILD"] = self.options.tbbmalloc
        if self.options.get_safe("interprocedural_optimization") is not None:
            tc.variables["TBB_ENABLE_IPO"] = self.options.interprocedural_optimization
        tc.variables["TBBMALLOC_PROXY_BUILD"] = self.options.tbbproxy
        tc.variables["TBB_DISABLE_HWLOC_AUTOMATIC_SEARCH"] = not self.options.get_safe("tbbbind", False)
        if self._tbbbind_explicit_hwloc:
            hwloc_dir = self.dependencies["hwloc"].package_folder
            hwloc_lib_name = ("hwloc.lib" if self.settings.os == "Windows" else
                              "libhwloc.dylib" if self.settings.os == "Macos" else
                              "libhwloc.so")
            tc.variables["CMAKE_HWLOC_2_LIBRARY_PATH"] = os.path.join(hwloc_dir, "lib", hwloc_lib_name).replace("\\", "/")
            tc.variables["CMAKE_HWLOC_2_INCLUDE_PATH"] = os.path.join(hwloc_dir, "include").replace("\\", "/")
            if self.settings.os == "Windows":
                tc.variables["CMAKE_HWLOC_2_DLL_PATH"] = os.path.join(hwloc_dir, "bin", "hwloc.dll").replace("\\", "/")
        tc.variables["TBB_BUILD_APPLE_FRAMEWORKS"] = self.options.get_safe("build_apple_frameworks", False)
        tc.generate()

        if self.options.get_safe("tbbbind") and not self._tbbbind_explicit_hwloc:
            deps = PkgConfigDeps(self)
            deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "TBB")
        self.cpp_info.set_property("pkg_config_name", "tbb")
        self.cpp_info.set_property("cmake_config_version_compat", "AnyNewerVersion")

        def lib_name(name):
            if self.settings.build_type == "Debug":
                return name + "_debug"
            return name

        # tbb
        tbb = self.cpp_info.components["libtbb"]

        tbb.set_property("cmake_target_name", "TBB::tbb")
        if self.options.get_safe("build_apple_frameworks"):
            tbb.frameworkdirs.append(os.path.join(self.package_folder, "lib"))
            tbb.frameworks.append("tbb")
        else:
            tbb.libs = [lib_name("tbb")]
        if self.settings.os == "Windows":
            version_info = load(self,
                os.path.join(self.package_folder, "include", "oneapi", "tbb",
                             "version.h"))
            binary_version = re.sub(
                r".*" + re.escape("#define __TBB_BINARY_VERSION ") +
                r"(\d+).*",
                r"\1",
                version_info,
                flags=re.MULTILINE | re.DOTALL,
            )
            tbb.libs.append(lib_name(f"tbb{binary_version}"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            tbb.system_libs = ["m", "dl", "rt", "pthread"]

        # tbbmalloc
        if self.options.tbbmalloc:
            tbbmalloc = self.cpp_info.components["tbbmalloc"]

            tbbmalloc.set_property("cmake_target_name", "TBB::tbbmalloc")

            if self.options.get_safe("build_apple_frameworks"):
                tbbmalloc.frameworkdirs.append(os.path.join(self.package_folder, "lib"))
                tbbmalloc.frameworks.append("tbbmalloc")
            else:
                tbbmalloc.libs = [lib_name("tbbmalloc")]

            if self.settings.os in ["Linux", "FreeBSD"]:
                tbbmalloc.system_libs = ["dl", "pthread"]

            # tbbmalloc_proxy
            if self.options.tbbproxy:
                tbbproxy = self.cpp_info.components["tbbmalloc_proxy"]

                tbbproxy.set_property("cmake_target_name", "TBB::tbbmalloc_proxy")

                if self.options.get_safe("build_apple_frameworks"):
                    tbbproxy.frameworkdirs.append(os.path.join(self.package_folder, "lib"))
                    tbbproxy.frameworks.append("tbbmalloc_proxy")
                else:
                    tbbproxy.libs = [lib_name("tbbmalloc_proxy")]

                tbbproxy.requires = ["tbbmalloc"]
                if self.settings.os in ["Linux", "FreeBSD"]:
                    tbbproxy.system_libs = ["m", "dl", "pthread"]
