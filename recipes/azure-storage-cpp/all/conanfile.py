import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime, is_msvc

required_conan_version = ">=2.1"


class AzureStorageCppConan(ConanFile):
    name = "azure-storage-cpp"
    description = "Microsoft Azure Storage Client Library for C++"
    license = "Apache-2.0"
    homepage = "https://github.com/Azure/azure-storage-cpp"
    topics = ("azure", "cpp", "cross-platform", "microsoft", "cloud")

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

    # Use azure-sdk-for-cpp::azure-storage-blobs-cpp instead
    # https://github.com/Azure/azure-sdk-for-cpp/blob/main/sdk/storage/MigrationGuide.md
    deprecated = "azure-sdk-for-cpp"

    def export_sources(self):
        copy(self, "CMakeLists.txt", src=self.recipe_folder, dst=self.export_sources_folder)
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cpprestsdk/2.10.19", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/[^2.12.5]", transitive_headers=True, transitive_libs=True)
        if self.settings.os != "Windows":
            # Boost.Asio is used in a public header here:
            # https://github.com/Azure/azure-storage-cpp/blob/v7.5.0/Microsoft.WindowsAzure.Storage/includes/wascore/timer_handler.h#L27
            self.requires("boost/[^1.74.0]", transitive_headers=True, libs=False)
            self.requires("util-linux-libuuid/[^2.41]", transitive_headers=True, transitive_libs=True)
            self.requires("openssl/[>=1.1 <4]")
        if is_apple_os(self):
            self.requires("gettext/[>=0.21 <1]")

    def validate(self):
        check_min_cppstd(self, 11)

        if self.options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration("Visual Studio build for shared library with MT runtime is not supported")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # CMake v4 support
        replace_in_file(self, "Microsoft.WindowsAzure.Storage/CMakeLists.txt",
                        "cmake_minimum_required(VERSION 2.6)",
                        "cmake_minimum_required(VERSION 3.8)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_FIND_FRAMEWORK"] = "LAST"
        tc.variables["BUILD_TESTS"] = False
        tc.variables["BUILD_SAMPLES"] = False
        if is_apple_os(self):
            tc.variables["GETTEXT_LIB_DIR"] = self.dependencies["libgettext"].cpp_info.libdir
        # Allow non-cache_variables to be used
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        # Relocatable shared libs on macOS
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0042"] = "NEW"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("util-linux-libuuid", "cmake_file_name", "UUID")
        deps.generate()

    def _patch_sources(self):
        cmakelists_path = os.path.join(self.source_folder, "Microsoft.WindowsAzure.Storage", "CMakeLists.txt")
        # Do not force C++11 and libc++
        replace_in_file(self, cmakelists_path, "-std=c++11", "")
        replace_in_file(self, cmakelists_path, "-stdlib=libc++", "")
        # Let Conan handle the Boost defines
        replace_in_file(self, cmakelists_path, "add_definitions(-DBOOST_LOG_DYN_LINK)", "")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder="..")
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        if self.settings.os == "Windows":
            # https://github.com/Azure/azure-storage-cpp/blob/v7.5.0/Microsoft.WindowsAzure.Storage/src/CMakeLists.txt#L100
            self.cpp_info.libs = ["wastorage"]
            # https://github.com/Azure/azure-storage-cpp/blob/v7.5.0/Microsoft.WindowsAzure.Storage/src/CMakeLists.txt#L90
            self.cpp_info.system_libs = ["ws2_32", "rpcrt4", "xmllite", "bcrypt"]
            if is_msvc(self):
                # https://github.com/Azure/azure-storage-cpp/blob/v7.5.0/Microsoft.WindowsAzure.Storage/CMakeLists.txt#L116-L120
                if self.options.shared:
                    self.cpp_info.defines = ["WASTORAGE_DLL", "_USRDLL"]
                else:
                    self.cpp_info.defines = ["_NO_WASTORAGE_API"]
        else:
            self.cpp_info.libs = ["azurestorage"]
