import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SdbusCppConan(ConanFile):
    name = "sdbus-cpp"
    license = "LicenseRef-LGPL-2.1-or-later-WITH-sdbus-cpp-LGPL-exception-1.0"
    homepage = "https://github.com/Kistler-Group/sdbus-cpp"
    description = "High-level C++ D-Bus library for Linux designed" \
                  " to provide easy-to-use yet powerful API in modern C++"
    topics = ("dbus", "sd-bus", "sdbus-c++")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_code_gen": [True, False],
        "with_sdbus": ["systemd", "basu"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_code_gen": False,
        "with_sdbus": "systemd",
    }

    @property
    def _minimum_cpp_standard(self):
        return 17

    @property
    def _minimum_compilers_version(self):
        # non-trivial designated initializers are not supported in gcc < 8
        # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=55606
        return {
            "gcc": "7" if Version(self.version) < "2.0.0" else "8",
            "clang": "6",
        }

    @property
    def _supported_os(self):
        return (["Linux"] if Version(self.version) < "1.4.0"
                else ["Linux", "FreeBSD"])

    @property
    def _with_sdbus(self):
        return ("basu" if self.settings.os == "FreeBSD"
                else self.options.get_safe("with_sdbus", "systemd"))

    def config_options(self):
        if Version(self.version) < "1.4.0" or self.settings.os != "Linux":
            del self.options.with_sdbus

    def configure(self):
        if Version(self.version) < "0.9.0":
            self.license = "LGPL-2.1-or-later"

        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self._with_sdbus == "systemd":
            self.requires("libsystemd/[^255]")
        elif self._with_sdbus == "basu":
            self.requires("basu/0.2.1")
        if self.options.with_code_gen:
            # Trick: always force transitive_libs=False, in order to not propagate expat lib
            # transitively even when sdbus-cpp is static, since expat is a dependency of the executable, not the lib
            self.requires("expat/[>=2.6.2 <3]", transitive_libs=False)

    def validate(self):
        if self.settings.os not in self._supported_os:
            raise ConanInvalidConfiguration(
                f"{self.ref} does not support {self.settings.os}")

        check_min_cppstd(self, self._minimum_cpp_standard)
        min_version = self._minimum_compilers_version.get(str(self.settings.compiler))
        if min_version and Version(self.settings.compiler.version) < min_version:
            raise ConanInvalidConfiguration("{} requires C++{} support. The current compiler {} {} does not support it.".format(
                self.name, self._minimum_cpp_standard, self.settings.compiler, self.settings.compiler.version))

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

        tc = CMakeToolchain(self)
        if Version(self.version) >= "2.0.0":
            tc.variables["SDBUSCPP_BUILD_CODEGEN"] = self.options.with_code_gen
        else:
            tc.variables["BUILD_CODE_GEN"] = self.options.with_code_gen
        tc.variables["BUILD_DOC"] = False
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_LIBSYSTEMD"] = False
        tc.variables["SDBUSCPP_BUILD_DOCS"] = False
        tc.variables["SDBUSCPP_SDBUS_LIB"] = self._with_sdbus
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        if self.options.with_code_gen:
            deps = CMakeDeps(self)
            deps.set_property("expat", "cmake_file_name", "EXPAT")
            deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.install()
        copy(self, "COPYING*", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sdbus-c++")
        self.cpp_info.set_property("cmake_target_name", "SDBusCpp::sdbus-c++")
        self.cpp_info.set_property("pkg_config_name", "sdbus-c++")
        self.cpp_info.libs = ["sdbus-c++"]
        self.cpp_info.system_libs = ["pthread", "m"]
