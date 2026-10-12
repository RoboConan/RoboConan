import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class PackageConan(ConanFile):
    name = "package"
    description = "short description"
    # Use short name only, conform to SPDX License List: https://spdx.org/licenses/
    # In case it's not listed there, use "DocumentRef-<license-file-name>:LicenseRef-<package-name>"
    license = ""
    homepage = "https://github.com/project/package"
    # Use topics from the upstream listed on GH. Include 'header-only' as a topic
    topics = ("topic1", "topic2", "topic3", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    # Do not copy sources to build folder for header only projects, unless you need to apply patches
    no_copy_source = True

    # Use the export_sources(self) method instead of the exports_sources attribute.
    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Direct dependencies of header only libs are always transitive since they are included in public headers
        self.requires("openssl/[<5]")

    # same package ID for any package
    def package_id(self):
        self.info.clear()

    def validate(self):
        check_min_cppstd(self, 14)
        # in case it does not work in another configuration, it should be validated here. Always comment the reason including the upstream issue.
        # INFO: Upstream does not support DLL: See <URL>
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} cannot be used on Windows.")

    def source(self):
        # Download source package and extract to source folder
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # The attribute no_copy_source should not be used when applying patches in build
        # Using patches is always the last resort to fix issues. If possible, try to fix the issue in the upstream project.
        apply_conandata_patches(self)

    # Copy all files to the package folder
    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Prefer CMake.install() or similar in case the upstream offers an official method to install the headers.
        copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        # Set these to the appropriate values if the package provides a CMake config file
        # (package-config.cmake or packageConfig.cmake, with package::package target, usually installed in <prefix>/lib/cmake/<package>/)
        self.cpp_info.set_property("cmake_file_name", "package")
        self.cpp_info.set_property("cmake_target_name", "package::package")
        # Set this to the appropriate value if the package provides a pkgconfig file
        # (package.pc, usually installed in <prefix>/lib/pkgconfig/)
        self.cpp_info.set_property("pkg_config_name", "package")

        # Folders not used for header-only
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        # Add m, pthread and dl if needed in Linux/FreeBSD
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
