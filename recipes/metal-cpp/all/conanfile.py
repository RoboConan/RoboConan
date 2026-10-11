import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import XCRun
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class MetalCppConan(ConanFile):
    name = "metal-cpp"
    description = (
        "Library for the usage of Apple Metal GPU programming in C++ applications - "
        "Header-only library to wrap Metal in C++ classes"
    )
    license = "Apache-2.0"
    homepage = "https://developer.apple.com/metal/cpp/"
    topics = ("metal", "gpu", "apple", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ["Macos", "iOS", "tvOS"]:
            raise ConanInvalidConfiguration("Metal-cpp only supports macOS, iOS and tvOS.")

        check_min_cppstd(self, 17)

        minimum_sdk_version = self.conan_data["minimum_sdk_version"][self.version][os_name]
        sdk_version = self.settings.get_safe("os.sdk_version")
        if sdk_version is None:
            sdk_version = XCRun(self).sdk_version
        if sdk_version is None:
            raise ConanInvalidConfiguration(
                f"metal-cpp {self.version} requires the os.sdk_version setting when the SDK cannot be detected"
            )
        if Version(sdk_version) < minimum_sdk_version:
            raise ConanInvalidConfiguration(
                f"metal-cpp {self.version} requires {os_name} SDK {minimum_sdk_version} or newer, but SDK {sdk_version} is configured"
            )

    def package(self):
        copy(self, "LICENSE.txt",
             os.path.join(self.source_folder),
             os.path.join(self.package_folder, "licenses"))
        copy(self, "**.hpp",
             os.path.join(self.source_folder),
             os.path.join(self.package_folder, "include"),
             keep_path=True)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.frameworks = ["Foundation", "Metal", "QuartzCore"]
        if Version(self.version) >= "14":
            self.cpp_info.frameworks.append("MetalFX")
