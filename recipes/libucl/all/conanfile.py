import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.4"

class LibuclConan(ConanFile):
    name = "libucl"
    description = "Universal configuration library parser"
    license = "BSD-2-Clause"
    homepage = "https://github.com/vstakhov/libucl"
    topics = ("universal", "configuration", "language", "parser", "ucl")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_url_include": [True, False],
        "enable_url_sign": [True, False],
        "with_lua": [False, "lua", "luajit"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_url_include": False,
        "enable_url_sign": False,
        "with_lua": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.enable_url_include:
            self.requires("libcurl/[>=7.78.0 <9]")
        if self.options.enable_url_sign:
            self.requires("openssl/[>=1.1 <4]")
        if self.options.with_lua == "lua":
            self.requires("lua/[^5.4.6]")
        elif self.options.with_lua == "luajit":
            self.requires("luajit/[>=2.1.0-beta3 <2.2]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_URL_INCLUDE"] = self.options.enable_url_include
        tc.variables["ENABLE_URL_SIGN"] = self.options.enable_url_sign
        tc.variables["ENABLE_LUA"] = self.options.with_lua == "lua"
        tc.variables["ENABLE_LUAJIT"] = self.options.with_lua == "luajit"
        tc.variables["ENABLE_UTILS"] = False
        tc.variables["ENABLE_SANITIZERS"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ucl")

        ucl = self.cpp_info.components["ucl"]
        ucl.libs = ["ucl"]
        ucl.set_property("cmake_target_name", "ucl::ucl")
        ucl.set_property("pkg_config_name", "libucl")
        if self.settings.os == "Windows" and not self.options.shared:
            ucl.defines.append("UCL_STATIC")

        if Version(self.version) >= "0.9.0" and self.settings.os in ["Linux", "FreeBSD"]:
            ucl.system_libs.append("m")

        if self.options.enable_url_include:
            ucl.requires.append("libcurl::curl")
        if self.options.enable_url_sign:
            ucl.requires.append("openssl::crypto")

        if self.options.with_lua:
            lua = self.cpp_info.components["lua"]
            lua.libs = ["lua-ucl"]
            lua.requires = ["ucl"]
            lua.set_property("cmake_target_name", "ucl::lua")
            if self.options.with_lua == "lua":
                lua.requires.append("lua::lua")
            else:
                lua.requires.append("luajit::luajit")
