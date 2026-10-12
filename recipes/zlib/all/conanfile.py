import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class ZlibConan(ConanFile):
    name = "zlib"
    package_type = "library"
    homepage = "https://zlib.net"
    license = "Zlib"
    description = ("A Massively Spiffy Yet Delicately Unobtrusive Compression Library "
                   "(Also Free, Not to Mention Unencumbered by Patents)")
    topics = ("zlib", "compression")

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
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if Version(self.version) >= "1.3.2":
            tc.cache_variables["ZLIB_INSTALL"] = True
            tc.cache_variables["ZLIB_BUILD_TESTING"] = False
            tc.cache_variables["ZLIB_BUILD_SHARED"] = self.options.shared
            tc.cache_variables["ZLIB_BUILD_STATIC"] = not self.options.shared
        else:
            tc.variables["SKIP_INSTALL_ALL"] = False
            tc.variables["SKIP_INSTALL_LIBRARIES"] = False
            tc.variables["SKIP_INSTALL_HEADERS"] = False
            tc.variables["SKIP_INSTALL_FILES"] = True
            # Correct for misuse of "${CMAKE_INSTALL_PREFIX}/" in CMakeLists.txt
            tc.variables["INSTALL_LIB_DIR"] = "lib"
            tc.variables["INSTALL_INC_DIR"] = "include"
            tc.variables["ZLIB_BUILD_EXAMPLES"] = False
        tc.generate()

    def _patch_sources(self):
        if Version(self.version) >= "1.3.2":
            return
        is_apple_clang12 = self.settings.compiler == "apple-clang" and Version(self.settings.compiler.version) >= "12.0"
        if not is_apple_clang12:
            for filename in ['zconf.h', 'zconf.h.cmakein', 'zconf.h.in']:
                filepath = os.path.join(self.source_folder, filename)
                replace_in_file(self, filepath,
                                      '#ifdef HAVE_UNISTD_H    '
                                      '/* may be set to #if 1 by ./configure */',
                                      '#if defined(HAVE_UNISTD_H) && (1-HAVE_UNISTD_H-1 != 0)')
                replace_in_file(self, filepath,
                                      '#ifdef HAVE_STDARG_H    '
                                      '/* may be set to #if 1 by ./configure */',
                                      '#if defined(HAVE_STDARG_H) && (1-HAVE_STDARG_H-1 != 0)')

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _extract_license(self):
        tmp = load(self, os.path.join(self.source_folder, "zlib.h"))
        license_contents = tmp[2:tmp.find("*/", 1)]
        return license_contents

    def package(self):
        if Version(self.version) >= "1.3.2":
            copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        else:
            save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), self._extract_license())
        cmake = CMake(self)
        cmake.install()
        if Version(self.version) >= "1.3.2":
            rmdir(self, os.path.join(self.package_folder, "share"))
            rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
            rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
            rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "ZLIB")
        self.cpp_info.set_property("pkg_config_name", "zlib")

        if Version(self.version) >= "1.3.2":
            target = "ZLIB::ZLIB" if self.options.shared else "ZLIB::ZLIBSTATIC"
            self.cpp_info.set_property("cmake_target_name", target)
            self.cpp_info.set_property("cmake_module_target_name", "ZLIB::ZLIB")
            if self.settings.os in ("Windows", "WindowsStore"):
                libname = "z" if self.options.shared else "zs"
                if self.settings.build_type == "Debug":
                    libname += "d"
            else:
                libname = "z"
        elif self.settings.os == "Windows" and self.settings.get_safe("compiler.runtime"):
            self.cpp_info.set_property("cmake_target_name", "ZLIB::ZLIB")
            # The recipe patches the CMakeLists.txt to generate different filenames when CMake
            # detects MINGW (clang, gcc with compiler.runtime undefined and compiler.libcxx defined)
            libname = "zdll" if self.options.shared else "zlib"
        else:
            self.cpp_info.set_property("cmake_target_name", "ZLIB::ZLIB")
            libname = "z"
        self.cpp_info.libs = [libname]
