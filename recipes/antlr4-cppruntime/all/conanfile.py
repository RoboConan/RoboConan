import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime

required_conan_version = ">=2.1"


class Antlr4CppRuntimeConan(ConanFile):
    name = "antlr4-cppruntime"
    description = "C++ runtime support for ANTLR (ANother Tool for Language Recognition)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/antlr/antlr4/tree/master/runtime/Cpp"
    topics = ("antlr", "parser", "runtime")

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

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ANTLR4_INSTALL"] = True
        tc.variables["WITH_LIBCXX"] = self.settings.compiler.get_safe("libcxx") == "libc++"
        tc.variables["ANTLR_BUILD_CPP_TESTS"] = False
        if is_msvc(self):
            tc.cache_variables["WITH_STATIC_CRT"] = is_msvc_static_runtime(self)
        tc.variables["WITH_DEMO"] = False
        # As of ANTLR 4.12.0, one can choose to build the shared/static library only instead of both of them
        # Related Issue: https://github.com/antlr/antlr4/issues/3993
        # Related PR: https://github.com/antlr/antlr4/pull/3996
        tc.variables["ANTLR_BUILD_SHARED"] = self.options.shared
        tc.variables["ANTLR_BUILD_STATIC"] = not self.options.shared
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder="runtime/Cpp")
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=os.path.join(self.source_folder), dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            rm(self, "*antlr4-runtime-static.*", os.path.join(self.package_folder, "lib"))
            rm(self, "*antlr4-runtime.a", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*.dll", os.path.join(self.package_folder, "bin"))
            rm(self, "antlr4-runtime.lib", os.path.join(self.package_folder, "lib"))
            rm(self, "*antlr4-runtime.so*", os.path.join(self.package_folder, "lib"))
            rm(self, "*antlr4-runtime.dll*", os.path.join(self.package_folder, "lib"))
            rm(self, "*antlr4-runtime.*dylib", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        # FIXME: this also removes lib/cmake/antlr4-generator
        # This cmake config script is needed to provide the cmake function `antlr4_generate`
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "antlr4-runtime")
        target_name = "antlr4_shared" if self.options.shared else "antlr4_static"
        target_alias = "antlr4_static" if self.options.shared else "antlr4_shared"
        self.cpp_info.set_property("cmake_target_name", target_name)
        self.cpp_info.set_property("cmake_target_aliases", [target_alias])
        libname = "antlr4-runtime"
        if is_msvc(self) and not self.options.shared:
            libname += "-static"
        self.cpp_info.libs = [libname]
        self.cpp_info.includedirs.append(os.path.join("include", "antlr4-runtime"))
        if self.settings.os == "Windows" and not self.options.shared:
            self.cpp_info.defines.append("ANTLR4CPP_STATIC")
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["m", "pthread"]
        elif is_apple_os(self):
            self.cpp_info.frameworks = ["CoreFoundation"]
