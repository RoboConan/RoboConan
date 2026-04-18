import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.4"


class HeatshrinkConan(ConanFile):
    name = "heatshrink"
    license = "ISC"
    description = "data compression library for embedded/real-time systems"
    topics = ("compression", "embedded", "realtime")
    homepage = "https://github.com/atomicobject/heatshrink"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [False, True],
        "fPIC": [True, False],
        "dynamic_alloc": [True, False],
        "debug_log": [True, False],
        "use_index": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "dynamic_alloc": True,
        "debug_log": False,
        "use_index": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["HEATSHRINK_SRC_DIR"] = self.source_folder.replace("\\", "/")
        tc.generate()

    def _patch_sources(self):
        config_file = os.path.join(self.source_folder, "heatshrink_config.h")
        if not self.options.dynamic_alloc:
            replace_in_file(self, config_file,
                "#define HEATSHRINK_DYNAMIC_ALLOC 1",
                "#define HEATSHRINK_DYNAMIC_ALLOC 0")
        if self.options.debug_log:
            replace_in_file(self, config_file,
                "#define HEATSHRINK_DEBUGGING_LOGS 0",
                "#define HEATSHRINK_DEBUGGING_LOGS 1")
        if not self.options.use_index:
            replace_in_file(self, config_file,
                "#define HEATSHRINK_USE_INDEX 1",
                "#define HEATSHRINK_USE_INDEX 0")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder="..")
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["heatshrink"]
