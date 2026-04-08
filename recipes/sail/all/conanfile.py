import os
import textwrap

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"

class SAILConan(ConanFile):
    name = "sail"
    package_type = "library"
    description = "The missing small and fast image decoding library for humans (not for machines)"
    homepage = "https://sail.software"
    topics = ( "image", "encoding", "decoding", "graphics" )
    license = "MIT"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "thread_safe": [True, False],
        "with_highest_priority_codecs": [True, False],
        "with_high_priority_codecs": [True, False],
        "with_medium_priority_codecs": [True, False],
        "with_low_priority_codecs": [True, False],
        "with_lowest_priority_codecs": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "thread_safe": True,
        "with_highest_priority_codecs": True,
        "with_high_priority_codecs": True,
        "with_medium_priority_codecs": True,
        "with_low_priority_codecs": True,
        "with_lowest_priority_codecs": True,
    }
    options_description = {
        "with_highest_priority_codecs": "Enable codecs: GIF, JPEG, PNG, TIFF",
        "with_high_priority_codecs": "Enable codecs: BMP, SVG",
        "with_medium_priority_codecs": "Enable codecs: AVIF, JPEG2000, JPEGXL, WEBL",
        "with_low_priority_codecs": "Enable codecs: ICO, PCX, PNM, PSD, QOI, TGA",
        "with_lowest_priority_codecs": "Enable codecs: WAL, XBM",
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_highest_priority_codecs:
            self.requires("giflib/[^5.2.1]")
            self.requires("libjpeg-meta/latest")
            self.requires("libpng/[~1.6]")
            self.requires("libtiff/[>=4.5 <5]")
        if self.options.with_high_priority_codecs:
            if Version(self.version) >= "0.9.1":
                self.requires("nanosvg/0.0+git.20231025")
        if self.options.with_medium_priority_codecs:
            self.requires("libavif/[^1.0.4]")
            self.requires("jasper/[^4.2]")
            self.requires("libjxl/0.8.2")
            self.requires("libwebp/[^1.3.2]")
        # used only in .c files
        self.requires("openmp/system")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], destination=self.source_folder)
        apply_conandata_patches(self)

    def generate(self):
        only_codecs = []

        if self.options.with_highest_priority_codecs:
            only_codecs.append("highest-priority")
        if self.options.with_high_priority_codecs:
            only_codecs.append("high-priority")
        if self.options.with_medium_priority_codecs:
            only_codecs.append("medium-priority")
        if self.options.with_low_priority_codecs:
            only_codecs.append("low-priority")
        if self.options.with_lowest_priority_codecs:
            only_codecs.append("lowest-priority")

        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"]       = False
        tc.variables["SAIL_BUILD_APPS"]     = False
        tc.variables["SAIL_BUILD_EXAMPLES"] = False
        tc.variables["SAIL_COMBINE_CODECS"] = True
        tc.variables["SAIL_ENABLE_OPENMP"]  = True
        tc.variables["SAIL_ONLY_CODECS"]    = ";".join(only_codecs)
        # SVG with nanosvg is supported in >= 0.9.1
        if Version(self.version) < "0.9.1":
            tc.variables["SAIL_DISABLE_CODECS"] = "svg"
        tc.variables["SAIL_INSTALL_PDB"]    = False
        tc.variables["SAIL_THREAD_SAFE"]    = self.options.thread_safe
        # TODO: Remove after fixing https://github.com/conan-io/conan/issues/12012
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        save(self, os.path.join(self.source_folder, "cmake", "sail_check_openmp.cmake"),
             textwrap.dedent("""\
                 function(sail_check_openmp)
                     find_package(OpenMP 3.0 COMPONENTS C REQUIRED)
                     set(SAIL_HAVE_OPENMP ON CACHE INTERNAL "")
                     set(SAIL_HAVE_OPENMP_DISPLAY ON CACHE INTERNAL "")
                 endfunction()
             """))

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt",       self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.INIH.txt",  self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.MUNIT.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Sail")

        self.cpp_info.components["sail-common"].set_property("cmake_target_name", "SAIL::SailCommon")
        self.cpp_info.components["sail-common"].set_property("pkg_config_name", "libsail-common")
        self.cpp_info.components["sail-common"].includedirs = ["include/sail"]
        self.cpp_info.components["sail-common"].libs = ["sail-common"]
        self.cpp_info.components["sail-common"].requires.append("openmp::openmp")

        self.cpp_info.components["sail-codecs"].set_property("cmake_target_name", "SAIL::SailCodecs")
        self.cpp_info.components["sail-codecs"].libs = ["sail-codecs"]
        self.cpp_info.components["sail-codecs"].requires = ["sail-common"]

        if self.options.with_highest_priority_codecs:
            self.cpp_info.components["sail-codecs"].requires.append("giflib::giflib")
            self.cpp_info.components["sail-codecs"].requires.append("libjpeg-meta::jpeg")
            self.cpp_info.components["sail-codecs"].requires.append("libpng::libpng")
            self.cpp_info.components["sail-codecs"].requires.append("libtiff::tiff")
            if Version(self.version) >= "0.9.1":
                self.cpp_info.components["sail-codecs"].requires.append("nanosvg::nanosvg")
        if self.options.with_medium_priority_codecs:
            self.cpp_info.components["sail-codecs"].requires.append("libavif::libavif")
            self.cpp_info.components["sail-codecs"].requires.append("jasper::jasper")
            self.cpp_info.components["sail-codecs"].requires.append("libjxl::libjxl")
            self.cpp_info.components["sail-codecs"].requires.append("libwebp::libwebp")

        self.cpp_info.components["libsail"].set_property("cmake_target_name", "SAIL::Sail")
        self.cpp_info.components["libsail"].set_property("pkg_config_name", "libsail")
        self.cpp_info.components["libsail"].libs = ["sail"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libsail"].system_libs.append("dl")
            if self.options.thread_safe:
                self.cpp_info.components["libsail"].system_libs.append("pthread")
        self.cpp_info.components["libsail"].requires = ["sail-common", "sail-codecs"]

        self.cpp_info.components["sail-manip"].set_property("cmake_target_name", "SAIL::SailManip")
        self.cpp_info.components["sail-manip"].set_property("pkg_config_name", "libsail-manip")
        self.cpp_info.components["sail-manip"].libs = ["sail-manip"]
        self.cpp_info.components["sail-manip"].requires = ["sail-common"]

        self.cpp_info.components["sail-c++"].set_property("cmake_target_name", "SAIL::SailC++")
        self.cpp_info.components["sail-c++"].set_property("pkg_config_name", "libsail-c++")
        self.cpp_info.components["sail-c++"].libs = ["sail-c++"]
        self.cpp_info.components["sail-c++"].requires = ["libsail", "sail-manip"]
