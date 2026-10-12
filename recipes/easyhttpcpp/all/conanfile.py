import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class EasyhttpcppConan(ConanFile):
    name = "easyhttpcpp"
    description = "A cross-platform HTTP client library with a focus on usability and speed"
    license = "MIT"
    topics = ("http", "client", "protocol")
    homepage = "https://github.com/sony/easyhttpcpp"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("poco/[^1.12.4]", transitive_headers=True, transitive_libs=True, options={
            opt: True for opt in self._required_poco_components
        })
        if self.settings.os != "Windows":
            self.requires("openssl/[<5]")

    @property
    def _required_poco_components(self):
        comps = ["enable_data", "enable_data_sqlite", "enable_net"]
        if self.settings.os == "Windows":
            comps.append("enable_netssl_win")
        else:
            comps.append("enable_netssl")
        return comps

    def validate(self):
        if any(not self.dependencies["poco"].options.get_safe(comp, False) for comp in self._required_poco_components):
            raise ConanInvalidConfiguration(
                f"{self.ref} requires the following poco options enabled: {', '.join(self._required_poco_components)}"
            )
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["FORCE_SHAREDLIB"] = self.options.shared
        if self.settings.os == "Windows" and self.options.shared:
            tc.preprocessor_definitions["EASYHTTPCPP_DLL"] = "1"
            tc.preprocessor_definitions["EASYHTTPCPP_API_EXPORTS"] = "1"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        if Version(self.version) > "2.1.0": # pylint: disable=conan-unreachable-upper-version
            raise ConanException("CMAKE_POLICY_VERSION_MINIMUM hardcoded to 3.5, check if new version supports CMake 4")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "easyhttpcppeasyhttp")
        self.cpp_info.set_property("cmake_target_name", "easyhttpcpp::easyhttp")
        libsuffix = ""
        if self.settings.build_type == "Debug":
            if self.settings.os == "Windows" and not self.options.shared:
                libsuffix += "md"
            libsuffix += "d"
        self.cpp_info.libs = [f"easyhttp{libsuffix}"]
        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.defines.append("EASYHTTPCPP_DLL")
        self.cpp_info.requires = [
            "poco::poco_foundation", "poco::poco_data",
            "poco::poco_datasqlite", "poco::poco_net",
        ]
        if self.settings.os == "Windows":
            self.cpp_info.requires.append("poco::poco_netsslwin")
        else:
            self.cpp_info.requires.extend(["poco::poco_netssl", "openssl::ssl"])
