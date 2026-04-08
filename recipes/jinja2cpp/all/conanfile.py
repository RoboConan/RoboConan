import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import msvc_runtime_flag, is_msvc

required_conan_version = ">=2.1"

class Jinja2cppConan(ConanFile):
    name = "jinja2cpp"
    description = "Jinja2 C++ (and for C++) almost full-conformance template engine implementation"
    license = "MIT"
    homepage = "https://jinja2cpp.dev/"
    topics = ("cpp14", "cpp17", "jinja2", "string templates", "templates engine")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_regex": ["std", "boost"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_regex": "boost",
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["boost"].with_filesystem = True
        self.options["boost"].with_json = True
        if self.options.with_regex == "boost":
            self.options["boost"].with_regex = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/[^1.79.0]")
        self.requires("expected-lite/[>=0.6.3 <1]", transitive_headers=True)
        self.requires("optional-lite/[^3.5.0]", transitive_headers=True)
        self.requires("rapidjson/[>=0.0+git.20250205]")
        self.requires("string-view-lite/1.7.0", transitive_headers=True)
        self.requires("variant-lite/2.0.0", transitive_headers=True)
        self.requires("nlohmann_json/[^3]")
        self.requires("fmt/[>=9 <11]")

    def validate(self):
        check_min_cppstd(self, 14)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.23 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Don't force MD for shared lib, honor the runtime from profile
        replace_in_file(self, "CMakeLists.txt", 'set(JINJA2CPP_MSVC_RUNTIME_TYPE "/MD")', "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["JINJA2CPP_USE_REGEX"] = self.options.with_regex
        tc.variables["JINJA2CPP_BUILD_TESTS"] = False
        tc.variables["JINJA2CPP_STRICT_WARNINGS"] = False
        tc.variables["JINJA2CPP_BUILD_SHARED"] = self.options.shared
        tc.variables["JINJA2CPP_DEPS_MODE"] = "conan-build"
        tc.cache_variables["JINJA2CPP_CXX_STANDARD"] = str(self.settings.compiler.cppstd).replace("gnu", "")
        if is_msvc(self):
            # Runtime type configuration for Jinja2C++ should be strictly '/MT' or '/MD'
            runtime = "/MD" if "MD" in msvc_runtime_flag(self) else "/MT"
            tc.variables["JINJA2CPP_MSVC_RUNTIME_TYPE"] = runtime
        tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("expected-lite", "cmake_target_name", "nonstd::expected-lite")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "jinja2cpp"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "jinja2cpp")
        self.cpp_info.set_property("cmake_target_name", "jinja2cpp")
        self.cpp_info.libs = ["jinja2cpp"]

