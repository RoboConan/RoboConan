import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibultrahdrConan(ConanFile):
    name = "libultrahdr"
    description = "libultrahdr is an image format for storing SDR and HDR versions of an image for android."
    license = "Apache-2.0"
    homepage = "https://github.com/google/libultrahdr"
    topics = ("ultrahdr", "graphics", "image", "hdr")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_gles": [True, False],
        "enable_intrinsics": [True, False],
        "enable_logs": [True, False],
        "write_iso": [True, False],
        "write_xmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_gles": False,
        "enable_intrinsics": True,
        "enable_logs": False,
        "write_iso": True,
        "write_xmp": False,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libjpeg-meta/latest")
        # TODO: might want to unvendor Google's image_io library as well

    def configure(self):
        if Version(self.version) >= "1.5":
            self.license = "Apache-2.0 OR MIT"

    def validate(self):
        check_min_cppstd(self, 17)
        if self.options.enable_gles and not self.options.shared:
            # The GLESv3/GLESv2 system lib deps cannot be predetermined.
            # Propagate them as dynamic library dependencies instead.
            raise ConanInvalidConfiguration("enable_gles option requires shared=True")


    def build_requirements(self):
        # Required for CMAKE_REQUIRE_FIND_PACKAGE_JPEG below
        self.tool_requires("cmake/[>=3.22 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Don't disable installation when cross-compiling
        replace_in_file(self, "CMakeLists.txt", "if(CMAKE_CROSSCOMPILING AND UHDR_ENABLE_INSTALL)", "if(FALSE)")
        if Version(self.version) < "1.5":
            # Conan expects CMP0091=NEW
            replace_in_file(self, "CMakeLists.txt", "cmake_policy(SET CMP0091 OLD)", "cmake_policy(SET CMP0091 NEW)")
        # Let Conan set cppstd
        replace_in_file(self, "CMakeLists.txt", "set(CMAKE_CXX_STANDARD 17)", "")
        # Must find libjpeg provided by Conan
        replace_in_file(self, "CMakeLists.txt", "find_package(JPEG QUIET)", "find_package(JPEG REQUIRED)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["UHDR_BUILD_DEPS"] = False
        tc.cache_variables["UHDR_BUILD_EXAMPLES"] = False
        tc.cache_variables["UHDR_BUILD_TESTS"] = False
        tc.cache_variables["UHDR_BUILD_BENCHMARK"] = False
        tc.cache_variables["UHDR_BUILD_FUZZERS"] = False
        tc.cache_variables["UHDR_BUILD_JAVA"] = False
        tc.cache_variables["UHDR_BUILD_PACKAGING"] = False
        tc.cache_variables["UHDR_ENABLE_INSTALL"] = True
        tc.cache_variables["UHDR_ENABLE_INTRINSICS"] = self.options.enable_intrinsics
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_JPEG"] = True
        tc.cache_variables["UHDR_ENABLE_GLES"] = self.options.enable_gles
        tc.cache_variables["UHDR_ENABLE_LOGS"] = self.options.enable_logs
        tc.cache_variables["UHDR_ENABLE_SMPTE2094_50"] = False
        tc.cache_variables["UHDR_ENABLE_WERROR"] = False
        tc.cache_variables["UHDR_WRITE_ISO"] = self.options.write_iso
        tc.cache_variables["UHDR_WRITE_XMP"] = self.options.write_xmp
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        if self.options.shared:
            # Don't build and install a static version in addition to the shared one
            save(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                 "\nset_target_properties(uhdr-static PROPERTIES EXCLUDE_FROM_ALL TRUE)\n",
                 append=True)
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            "install(TARGETS ${UHDR_TARGET_NAME} ${UHDR_TARGET_NAME_STATIC} ",
                            "install(TARGETS ${UHDR_TARGET_NAME} ")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libuhdr")
        self.cpp_info.libs = ["uhdr"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m", "pthread"]
        elif self.settings.os == "Android":
            self.cpp_info.system_libs = ["log"]
        self.cpp_info.requires = ["libjpeg-meta::jpeg"]
