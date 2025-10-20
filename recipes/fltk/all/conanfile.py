import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import msvc_runtime_flag
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class FltkConan(ConanFile):
    name = "fltk"
    description = "Fast Light Toolkit is a cross-platform C++ GUI toolkit"
    license = "LGPL-2.1-or-later WITH FLTK-exception"
    homepage = "https://www.fltk.org"
    topics = ("gui",)

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_gl": [True, False],
        "with_threads": [True, False],
        "with_gdiplus": [True, False],
        "abi_version": ["ANY"],
        "with_pango": [True, False],
        "with_xft": [True, False],
        "with_wayland": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_gl": True,
        "with_threads": True,
        "with_gdiplus": True,
        "with_pango": False,
        "with_xft": False,
        "with_wayland": False,
    }

    @property
    def _is_cl_like(self):
        return self.settings.compiler.get_safe("runtime") is not None

    @property
    def _is_cl_like_static_runtime(self):
        return self._is_cl_like and "MT" in msvc_runtime_flag(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            del self.options.with_gdiplus

        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_pango
            del self.options.with_xft
            del self.options.with_wayland

        if self.options.abi_version == None:
            version = Version(self.version + ".0")
            self.options.abi_version = str(int(version.major.value) * 10000 +
                                           int(version.minor.value) * 100 +
                                           int(version.patch.value))

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.get_safe("with_wayland"):
            self.options.with_pango.value = True
            self.options.with_gl.value = True
        if self.options.get_safe("with_pango"):
            self.options.with_xft.value = True
            self.options["pango"].with_cairo = True
            self.options["pango"].with_freetype = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        self.requires("libjpeg-meta/latest")
        self.requires("libpng/[~1.6]")
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.options.with_gl:
                self.requires("opengl/system")
                self.requires("egl/system")
                self.requires("glu/system")
            self.requires("fontconfig/[^2.15.0]")
            self.requires("xorg/system")
            if self.options.with_pango:
                self.requires("pango/[^1.54.0]")
            if self.options.with_xft:
                self.requires("libxft/[^2.3.8]")
            if self.options.with_wayland:
                self.requires("wayland/[^1.22.0]")
                self.requires("xkbcommon/[^1.6.0]")
                self.requires("libdecor/[>=0.2.2 <1]")
                self.requires("dbus/[^1.15]")

    def build_requirements(self):
        if self.options.get_safe("with_wayland"):
            self.tool_requires("wayland/<host_version>")
        if self.settings.os in ["Linux", "FreeBSD"]:
            if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
                self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Use libxft CMake target instead of relying on find_library for it and its dependencies.
        replace_in_file(self, "src/CMakeLists.txt",
                        "  list(APPEND OPTIONAL_LIBS ${X11_Xft_LIB})",
                        "  find_package(libxft REQUIRED)\n"
                        "  list(APPEND OPTIONAL_LIBS libxft::libxft)\n")
        # Use CMake targets directly instead of their INTERFACE_LINK_LIBRARIES property, which breaks with CMakeDeps.
        replace_in_file(self, "src/CMakeLists.txt",
                        "if(_link_libraries)",
                        "list(APPEND OPTIONAL_LIBS ${_target})\n"
                        "if(FALSE)")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["FLTK_BUILD_TEST"] = False
        tc.cache_variables["FLTK_BUILD_EXAMPLES"] = False
        tc.cache_variables["FLTK_BUILD_HTML_DOCS"] = False
        tc.cache_variables["FLTK_BUILD_PDF_DOCS"] = False
        tc.cache_variables["FLTK_BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["FLTK_BUILD_GL"] = self.options.with_gl
        tc.cache_variables["FLTK_USE_PTHREADS"] = self.options.with_threads
        tc.cache_variables["FLTK_USE_PANGO"] = self.options.get_safe("with_pango", False)
        tc.cache_variables["FLTK_GRAPHICS_CAIRO"] = self.options.get_safe("with_pango", False)
        tc.cache_variables["FLTK_USE_XFT"] = self.options.get_safe("with_xft", False)
        tc.cache_variables["FLTK_BACKEND_WAYLAND"] = self.options.get_safe("with_wayland", False)
        tc.cache_variables["FLTK_USE_SYSTEM_LIBDECOR"] = True
        tc.cache_variables["FLTK_ABI_VERSION"] = self.options.abi_version
        tc.cache_variables["FLTK_USE_SYSTEM_LIBJPEG"] = True
        tc.cache_variables["FLTK_USE_SYSTEM_ZLIB"] = True
        tc.cache_variables["FLTK_USE_SYSTEM_LIBPNG"] = True
        tc.cache_variables["FLTK_BUILD_FLUID"] = False
        if self._is_cl_like:
            tc.cache_variables["FLTK_MSVC_RUNTIME_DLL"] = not self._is_cl_like_static_runtime
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        if self.settings.os in ["Linux", "FreeBSD"]:
            deps = PkgConfigDeps(self)
            deps.set_property("opengl", "pkg_config_name", "gl")
            deps.generate()

    def _patch_sources(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            # Fix relocated X11 and OpenGL not being linked against correctly
            replace_in_file(self, os.path.join(self.source_folder, "CMake", "options.cmake"),
                            "include(FindX11)",
                            "find_package(X11 REQUIRED)\n"
                            "link_libraries(X11::X11 X11::Xext)\n" +
                            ("find_package(OpenGL REQUIRED)\n"
                             "link_libraries(OpenGL::GLX)\n" if self.options.with_gl else ""))

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "FLTK.framework"))
        rmdir(self, os.path.join(self.package_folder, "CMake"))
        rm(self, "fltk-config*", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fltk")
        self.cpp_info.set_property("cmake_target_name", "fltk::fltk")
        self.cpp_info.libs = collect_libs(self)

        if self.settings.os in ("Linux", "FreeBSD"):
            if self.options.with_threads:
                self.cpp_info.system_libs.extend(["pthread", "dl"])
        elif is_apple_os(self):
            self.cpp_info.frameworks = [
                "AppKit", "ApplicationServices", "Carbon", "Cocoa", "CoreFoundation", "CoreGraphics",
                "CoreText", "CoreVideo", "Foundation", "IOKit",
            ]
            self.cpp_info.sharedlinkflags.append("-Wl,-weak_framework,ScreenCaptureKit")
            self.cpp_info.exelinkflags.append("-Wl,-weak_framework,ScreenCaptureKit")
            if self.options.with_gl:
                self.cpp_info.frameworks.append("OpenGL")
        elif self.settings.os == "Windows":
            if self.options.shared:
                self.cpp_info.defines.append("FL_DLL")
            self.cpp_info.system_libs = ["gdi32", "imm32", "msimg32", "ole32", "oleaut32", "uuid", "comctl32"]
            if self.options.get_safe("with_gdiplus"):
                self.cpp_info.system_libs.append("gdiplus")
            if self.options.with_gl:
                self.cpp_info.system_libs.append("opengl32")
            self.cpp_info.system_libs.append("ws2_32")

        self.cpp_info.requires = [
            "zlib-ng::zlib-ng",
            "libjpeg-meta::jpeg",
            "libpng::libpng",
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.requires.extend([
                "fontconfig::fontconfig",
                # https://github.com/fltk/fltk/blob/release-1.3.9/CMake/options.cmake#L466-L551
                "xorg::xinerama",
                "xorg::xfixes",
                "xorg::xcursor",
                "xorg::xrender",
                "xorg::x11", # Also includes Xdbe
                # https://github.com/fltk/fltk/blob/release-1.3.9/CMake/options.cmake#L236
                "xorg::xext",
            ])
            if self.options.with_pango:
                self.cpp_info.requires.extend(["pango::pango_", "pango::pangocairo", "pango::pangoxft"])
            if self.options.with_xft:
                self.cpp_info.requires.append("libxft::libxft")
            if self.options.with_gl:
                self.cpp_info.requires.extend(["opengl::opengl", "egl::egl", "glu::glu"])
            if self.options.with_wayland:
                self.cpp_info.requires.extend([
                    "wayland::wayland",
                    "xkbcommon::xkbcommon",
                    "libdecor::libdecor",
                    "dbus::dbus",
                ])
