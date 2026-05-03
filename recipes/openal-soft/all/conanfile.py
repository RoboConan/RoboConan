import os
import textwrap

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OpenALSoftConan(ConanFile):
    name = "openal-soft"
    description = "OpenAL Soft is a software implementation of the OpenAL 3D audio API."
    topics = ("openal", "audio", "api")
    homepage = "https://openal-soft.org/"
    license = "LGPL-2.0-or-later"
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

    def package_id(self):
        # OpenAL's API is pure C, thus the C++ standard does not matter
        # Because the backend is C++, the C++ STL matters
        del self.info.settings.compiler.cppstd

    def requirements(self):
        self.requires("fmt/[>=10]")
        if self.settings.os == "Linux":
            self.requires("libalsa/[^1.2.10]")

    def validate(self):
        check_min_cppstd(self, 14)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["LIBTYPE"] = "SHARED" if self.options.shared else "STATIC"
        tc.variables["ALSOFT_UTILS"] = False
        tc.variables["ALSOFT_EXAMPLES"] = False
        tc.variables["ALSOFT_TESTS"] = False
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_SoundIO"] = True
        if Version(self.version) < "1.24.0": # pylint: disable=conan-condition-evals-to-constant
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        self._create_cmake_module_variables(
            os.path.join(self.package_folder, self._module_file_rel_path)
        )

    def _create_cmake_module_variables(self, module_file):
        content = textwrap.dedent(f"""\
            set(OPENAL_FOUND TRUE)
            if(DEFINED OpenAL_INCLUDE_DIR)
                set(OPENAL_INCLUDE_DIR ${{OpenAL_INCLUDE_DIR}})
            endif()
            if(DEFINED OpenAL_LIBRARIES)
                set(OPENAL_LIBRARY ${{OpenAL_LIBRARIES}})
            endif()
            set(OPENAL_VERSION_STRING {self.version})
        """)
        save(self, module_file, content)

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-variables.cmake")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "OpenAL")
        self.cpp_info.set_property("cmake_target_name", "OpenAL::OpenAL")
        self.cpp_info.set_property("cmake_build_modules", [self._module_file_rel_path])
        self.cpp_info.set_property("pkg_config_name", "openal")

        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.includedirs.append(os.path.join("include", "AL"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["dl", "m"])
        elif is_apple_os(self):
            self.cpp_info.frameworks.extend(["AudioToolbox", "AudioUnit", "CoreAudio", "CoreFoundation"])
            if self.settings.os == "Macos":
                self.cpp_info.frameworks.append("ApplicationServices")
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs.extend(["winmm", "ole32", "shell32", "user32"])
        if not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.system_libs.append(libcxx)
        if not self.options.shared:
            self.cpp_info.defines.append("AL_LIBTYPE_STATIC")
        if self.settings.get_safe("compiler.libcxx") in ["libstdc++", "libstdc++11"]:
            self.cpp_info.system_libs.append("atomic")
