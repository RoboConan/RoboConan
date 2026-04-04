import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class LibavrocppConan(ConanFile):
    name = "libavrocpp"
    description = "Avro is a data serialization system."
    license = "Apache-2.0"
    homepage = "https://avro.apache.org/"
    topics = ("serialization", "deserialization","avro")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    @property
    def _boost_components(self):
        return ["filesystem", "iostreams", "program_options", "regex"]

    def requirements(self):
        self.requires("boost/[^1.74.0]", transitive_headers=True, options={
            f"with_{comp}": True for comp in self._boost_components
        })
        self.requires("snappy/[^1.1.9]")

    def validate(self):
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # CMake v4 support
        if Version(self.version) >= "1.11.0":
            replace_in_file(self, "lang/c++/CMakeLists.txt",
                            "cmake_minimum_required (VERSION 3.1)",
                            "cmake_minimum_required (VERSION 3.5)")
        else:
            replace_in_file(self, "lang/c++/CMakeLists.txt",
                            "cmake_minimum_required (VERSION 2.6)",
                            "cmake_minimum_required (VERSION 3.5)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        cmakelists = os.path.join(self.source_folder, "lang", "c++", "CMakeLists.txt")
        # Fix discovery & link to Snappy
        replace_in_file(self, cmakelists, "SNAPPY_FOUND", "Snappy_FOUND")
        replace_in_file(self, cmakelists, "${SNAPPY_LIBRARIES}", "Snappy::snappy")
        replace_in_file(
            self, cmakelists,
            "target_include_directories(avrocpp_s PRIVATE ${SNAPPY_INCLUDE_DIR})",
            "target_link_libraries(avrocpp_s PRIVATE Snappy::snappy)",
        )
        # Install either static or shared
        target = "avrocpp" if self.options.shared else "avrocpp_s"
        replace_in_file(self, cmakelists, "install (TARGETS avrocpp avrocpp_s" , f"install (TARGETS {target}")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder="lang/c++")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "Windows":
            for dll_pattern_to_remove in ["concrt*.dll", "msvcp*.dll", "vcruntime*.dll"]:
                rm(self, dll_pattern_to_remove, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["avrocpp"] if self.options.shared else ["avrocpp_s"]
        if self.options.shared:
            self.cpp_info.defines.append("AVRO_DYN_LINK")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        self.cpp_info.requires = [f"boost::{comp}" for comp in self._boost_components]
        self.cpp_info.requires.append("snappy::snappy")
