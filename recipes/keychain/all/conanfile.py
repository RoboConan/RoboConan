import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps


class KeychainConan(ConanFile):
    name = "keychain"
    description = "A cross-platform wrapper for the operating system's credential storage"
    license = "MIT"
    homepage = "https://github.com/hrantzsch/keychain"
    topics = ("keychain", "security", "credentials", "password", "cpp11")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [False, True],
        "fPIC": [False, True],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.settings.os == "Linux":
            self.requires("libsecret/[>=0.20.5 <1]")
            self.requires("glib/[^2.70.0]")

    def validate(self):
        check_min_cppstd(self, 11)

    def build_requirements(self):
        if self.settings.os == "Linux":
            if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
                self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Ensure .dll is installed on Windows
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            "TARGETS ${PROJECT_NAME}",
            "TARGETS ${PROJECT_NAME} RUNTIME DESTINATION bin",
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = False
        # Export all symbols by default to allow generating a shared library with msvc
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.generate()
        pc = PkgConfigDeps(self)
        pc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            pattern="LICENSE",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)

        if self.settings.os == "Macos":
            self.cpp_info.frameworks = ["Security", "CoreFoundation"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["crypt32"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
