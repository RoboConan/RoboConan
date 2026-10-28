import os
from functools import cached_property

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class NautyConan(ConanFile):
    name = "nauty"
    description = "Graph canonical labeling and automorphism group computation"
    license = "Apache-2.0"
    homepage = "https://pallini.di.uniroma1.it/"
    topics = ("graph-theory", "automorphism", "isomorphism")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "tls": [True, False],
        "wordsize": [16, 32, 64, 128],
        "small": [True, False],
    }
    default_options = {
        "fPIC": True,
        "tls": True,
        "wordsize": 64,
        "small": False,
    }
    options_description = {
        "tls": "Enable thread-local storage. Makes the library thread-safe,"
               " but may slow it down slightly if you aren’t using threads.",
        "wordsize": "The size of a single 'setword' in bits."
                    " I.e. how many set elements can be stored by a single setword integer value.",
        "small": "Set the maximum order of a graph to the wordsize value.",
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "CMakeLists.txt", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if "64" in str(self.settings.arch) or self.settings.arch in ["armv8", "armv8.3"]:
            self.options.wordsize = 64
        else:
            self.options.wordsize = 32

    @cached_property
    def _libname(self):
        libname = "nauty"
        if self.options.tls:
            libname += "T"
        libname += {16: "S", 32: "W", 64: "L", 128: "Q"}[int(self.options.wordsize.value)]
        if self.options.small:
            libname += "1"
        return libname

    def layout(self):
        cmake_layout(self, src_folder="src")

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if is_msvc(self):
            self.tool_requires("automake/[^1.18.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.tls:
            tc.configure_args.append("--enable-tls")
        else:
            tc.configure_args.append("--disable-tls")
        tc.generate()

        if is_msvc(self):
            env = Environment()
            compile_wrapper = unix_path(self, self.dependencies.build["automake"].conf_info.get("user.automake:compile-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.vars(self).save_script("conanbuild_msvc")

        tc = CMakeToolchain(self)
        tc.cache_variables["NAUTY_OUTPUT_NAME"] = self._libname
        tc.preprocessor_definitions["WORDSIZE"] = self.options.wordsize
        if self.options.small:
            tc.preprocessor_definitions["MAXN"] = "WORDSIZE"
        if self.options.tls:
            tc.preprocessor_definitions["USE_TLS"] = None
        tc.generate()

    def build(self):
        # Let Autotools generate the config header
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.configure()

        if is_msvc(self):
            # Match the Windows convention and typedef for booleans
            replace_in_file(self, os.path.join(self.source_folder, "nauty.h"),
                            "typedef int boolean;",
                            "typedef unsigned char boolean;")

        # Build with CMake for MSVC and shared library output support
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYRIGHT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE-2.0.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_target_aliases", ["nauty", self._libname])
        self.cpp_info.set_property("pkg_config_name", self._libname)
        self.cpp_info.set_property("pkg_config_aliases", ["nauty"])
        self.cpp_info.libs = [self._libname]
        self.cpp_info.defines = [f"WORDSIZE={self.options.wordsize}"]
        if self.options.small:
            self.cpp_info.defines.append("MAXN=WORDSIZE")
        if self.options.tls:
            self.cpp_info.defines.append("USE_TLS")
