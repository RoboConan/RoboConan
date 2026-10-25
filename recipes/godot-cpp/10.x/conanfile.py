import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime

required_conan_version = ">=2.1"


class GodotCppConan(ConanFile):
    name = "godot-cpp"
    description = "C++ bindings for the Godot Engine's GDExtension API"
    license = "MIT"
    homepage = "https://github.com/godotengine/godot-cpp"
    topics = ("godot", "game-engine", "game-development", "gdextension", "bindings", "c++")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "api_version": ["4.3", "4.4", "4.5", "4.6", "4.7"],
        "target": ["template_debug", "template_release", "editor"],
        "generate_template_get_node": [True, False],
        "precision": ["single", "double"],
        "threads": [True, False],
        "use_hot_reload": [True, False],
        "exceptions": [True, False],
        "deprecated": [True, False],
        "dev_build": [True, False],
        "symbol_visibility": ["auto", "visible", "hidden"],
    }
    default_options = {
        "api_version": "4.7",
        "target": "template_debug",
        "generate_template_get_node": True,
        "precision": "single",
        "threads": True,
        "use_hot_reload": False,
        "exceptions": False,
        "deprecated": True,
        "dev_build": False,
        "symbol_visibility": "hidden",
    }

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ["Windows", "Linux", "Macos", "iOS", "Android", "Emscripten"]:
            raise ConanInvalidConfiguration(f"godot-cpp does not support {self.settings.os}")
        if self.settings.os == "Emscripten" and self.settings.arch != "wasm":
            raise ConanInvalidConfiguration("godot-cpp requires arch=wasm on Emscripten")
        check_min_cppstd(self, 17)

    def build_requirements(self):
        self.tool_requires("cpython/[^3.12]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "cmake/godotcpp.cmake",
                        'OUTPUT_NAME "${PROJECT_NAME}${GODOTCPP_SUFFIX}"',
                        'OUTPUT_NAME "${PROJECT_NAME}"')

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["GODOTCPP_API_VERSION"] = self.options.api_version
        tc.cache_variables["GODOTCPP_TARGET"] = self.options.target
        tc.cache_variables["GODOTCPP_GENERATE_TEMPLATE_GET_NODE"] = self.options.generate_template_get_node
        tc.cache_variables["GODOTCPP_PRECISION"] = self.options.precision
        tc.cache_variables["GODOTCPP_THREADS"] = self.options.threads
        tc.cache_variables["GODOTCPP_USE_HOT_RELOAD"] = self.options.use_hot_reload
        tc.cache_variables["GODOTCPP_DISABLE_EXCEPTIONS"] = not self.options.exceptions
        tc.cache_variables["GODOTCPP_DEPRECATED"] = self.options.deprecated
        tc.cache_variables["GODOTCPP_DEV_BUILD"] = self.options.dev_build
        tc.cache_variables["GODOTCPP_SYMBOL_VISIBILITY"] = self.options.symbol_visibility
        tc.cache_variables["GODOTCPP_ENABLE_TESTING"] = False
        if self.options.target == "editor":
            tc.preprocessor_definitions["TOOLS_ENABLED"] = None
        if self.settings.os in ["Linux", "Windows"]:
            use_static_cpp = is_msvc_static_runtime(self) if is_msvc(self) else False
            tc.cache_variables["GODOTCPP_USE_STATIC_CPP"] = use_static_cpp
        if is_msvc(self):
            tc.cache_variables["GODOTCPP_DEBUG_CRT"] = self.settings.build_type == "Debug"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        copy(self, "*.inc", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        copy(self, "*.h", os.path.join(self.build_folder, "gen", "include"), os.path.join(self.package_folder, "include"))
        copy(self, "*.hpp", os.path.join(self.build_folder, "gen", "include"), os.path.join(self.package_folder, "include"))
        copy(self, "*.inc", os.path.join(self.build_folder, "gen", "include"), os.path.join(self.package_folder, "include"))
        bin_dir = os.path.join(self.build_folder, "bin")
        copy(self, "*.a", bin_dir, os.path.join(self.package_folder, "lib"))
        copy(self, "*.lib", bin_dir, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["libgodot-cpp" if is_msvc(self) else "godot-cpp"]
        self.cpp_info.defines = ["GDEXTENSION"]
        if self.options.target != "template_release":
            self.cpp_info.defines.append("DEBUG_ENABLED")
        if self.options.target == "editor":
            self.cpp_info.defines.append("TOOLS_ENABLED")
        if self.options.dev_build:
            self.cpp_info.defines.append("DEV_ENABLED")
        if self.options.use_hot_reload:
            self.cpp_info.defines.append("HOT_RELOAD_ENABLED")
        if self.options.precision == "double":
            self.cpp_info.defines.append("REAL_T_IS_DOUBLE")
        if self.options.threads:
            self.cpp_info.defines.append("THREADS_ENABLED")
        if not self.options.deprecated:
            self.cpp_info.defines.append("DISABLE_DEPRECATED")
        if is_msvc(self) and not self.options.exceptions:
            self.cpp_info.defines.append("_HAS_EXCEPTIONS=0")

        platform_defines = {
            "Android": ["ANDROID_ENABLED", "UNIX_ENABLED"],
            "iOS": ["IOS_ENABLED", "UNIX_ENABLED"],
            "Linux": ["LINUX_ENABLED", "UNIX_ENABLED"],
            "Macos": ["MACOS_ENABLED", "UNIX_ENABLED"],
            "Emscripten": ["WEB_ENABLED", "UNIX_ENABLED"],
            "Windows": ["WINDOWS_ENABLED"],
        }
        self.cpp_info.defines.extend(platform_defines.get(str(self.settings.os), []))
        if is_msvc(self):
            self.cpp_info.defines.extend(["TYPED_METHOD_BIND", "NOMINMAX"])
            self.cpp_info.cxxflags.extend(["/utf-8", "/Zc:__cplusplus"])
        if self.options.use_hot_reload and self.settings.compiler == "gcc":
            self.cpp_info.cxxflags.append("-fno-gnu-unique")
        if self.settings.os == "Emscripten":
            self.cpp_info.cxxflags.extend([
                "-sSIDE_MODULE=1",
                "-sSUPPORT_LONGJMP=wasm",
            ])
            web_linkflags = [
                "-sWASM_BIGINT",
                "-sSUPPORT_LONGJMP=wasm",
                "-fvisibility=hidden",
            ]
            self.cpp_info.exelinkflags.extend(web_linkflags)
            self.cpp_info.sharedlinkflags.extend(web_linkflags + ["-shared"])
            if self.options.threads:
                self.cpp_info.cxxflags.append("-sUSE_PTHREADS=1")
                self.cpp_info.exelinkflags.append("-sUSE_PTHREADS=1")
                self.cpp_info.sharedlinkflags.append("-sUSE_PTHREADS=1")
