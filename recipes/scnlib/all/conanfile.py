import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"

class ScnlibConan(ConanFile):
    name = "scnlib"
    description = "scanf for modern C++"
    license = "Apache-2.0"
    homepage = "https://github.com/eliaskosunen/scnlib"
    topics = ("parsing", "io", "scanf")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "regex_backend": ["None", "std", "boost", "boost_icu", "re2"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "regex_backend": "std",
    }

    @property
    def _min_cppstd(self):
        # scn/2.0.0 has complation error on MSVC c++17
        # we have to use versions which support c++20
        # https://github.com/eliaskosunen/scnlib/issues/97
        # https://github.com/conan-io/conan-center-index/pull/22455#issuecomment-1924444193
        return "20" if is_msvc(self) else "17"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.regex_backend in ["boost", "boost_icu"]:
            self.options["boost"].with_regex = True
        if self.options.regex_backend == "boost_icu":
            self.options["boost"].i18n_backend_icu = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("fast_float/[<9]")
        if Version(self.version) < "3.0":
            self.requires("simdutf/4.0.5")
        if self.options.regex_backend in ["boost", "boost_icu"]:
            self.requires("boost/[^1.71.0]")
        elif self.options.regex_backend == "re2":
            self.requires("re2/[>=20220601]")

    def validate(self):
        check_min_cppstd(self, self._min_cppstd)

        if self.options.regex_backend == "boost_icu" and not self.dependencies["boost"].options.get_safe("i18n_backend_icu"):
            raise ConanInvalidConfiguration(
                f"{self.ref} with regex_backend=Boost_icu option requires boost::i18n_backend_icu to be enabled."
            )
        if Version(self.version) < "3.0.2" and self.settings.compiler == "gcc" and Version(self.settings.compiler.version).major == "11":
            raise ConanInvalidConfiguration(f"{self.ref} doesn't support gcc 11.x due to std::regex_constants::multiline is not defined.")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.16 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SCN_TESTS"] = False
        tc.variables["SCN_EXAMPLES"] = False
        tc.variables["SCN_BENCHMARKS"] = False
        tc.variables["SCN_DOCS"] = False
        tc.variables["SCN_INSTALL"] = True
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.variables["SCN_USE_EXTERNAL_SIMDUTF"] = True
        tc.variables["SCN_USE_EXTERNAL_FAST_FLOAT"] = True
        tc.variables["SCN_BENCHMARKS_BUILDTIME"] = False
        tc.variables["SCN_BENCHMARKS_BINARYSIZE"] = False
        tc.variables["SCN_DISABLE_REGEX"] = self.options.regex_backend is None
        if self.options.regex_backend is not None:
            tc.variables["SCN_REGEX_BACKEND"] = self.options.regex_backend
            tc.variables["SCN_USE_EXTERNAL_REGEX_BACKEND"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.cmake", os.path.join(self.package_folder, "include", "scn", "detail"))
        rmdir(self, os.path.join(self.package_folder, "include", "scn", "detail", "CMakeFiles"))
        rmdir(self, os.path.join(self.package_folder, "include", "scn", "detail", "deps", "CMakeFiles"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "scn")
        self.cpp_info.set_property("cmake_target_name", f"scn::scn")
        self.cpp_info.libs = ["scn"]
        self.cpp_info.defines = ["SCN_HEADER_ONLY=0"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
