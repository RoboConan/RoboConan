import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.build import stdcpp_library
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc_static_runtime, is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class HarfbuzzConan(ConanFile):
    name = "harfbuzz"
    description = "HarfBuzz is an OpenType text shaping engine."
    topics = ("opentype", "text", "engine")
    homepage = "https://harfbuzz.github.io/"
    license = "MIT"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_freetype": [True, False],
        "with_icu": [True, False],
        "with_glib": [True, False],
        "with_gdi": [True, False],
        "with_uniscribe": [True, False],
        "with_directwrite": [True, False],
        "with_coretext": [True, False],
        "with_introspection": [True, False],
        "with_png": [True, False],
        "with_zlib": [True, False],
        "with_raster": [True, False],
        "with_vector": [True, False],
        "with_gpu": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_freetype": True,
        "with_icu": False,
        "with_glib": True,
        "with_gdi": True,
        "with_uniscribe": True,
        "with_directwrite": False,
        "with_coretext": True,
        "with_introspection": False,
        "with_png": True,
        "with_zlib": True,
        "with_raster": True,
        "with_vector": True,
        "with_gpu": True,
    }

    python_requires = "conan-utils/latest"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            del self.options.with_gdi
            del self.options.with_uniscribe
            del self.options.with_directwrite
        if not is_apple_os(self):
            del self.options.with_coretext
        if Version(self.version) < "14.0.0":
            del self.options.with_png
            del self.options.with_zlib
            del self.options.with_raster
            del self.options.with_vector
            del self.options.with_gpu

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.shared and self.options.with_glib:
            self.options["glib"].shared = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_glib:
            self.requires("glib/[^2.70.0]")
            if self.options.with_introspection:
                self.requires("gobject-introspection/[^1.82]", options={"build_introspection_data": True})
                self.requires("glib-gir/[^2.82]")
        if self.options.with_freetype:
            self.requires("freetype/[^2.13.2]")
        if self.options.with_icu:
            self.requires("icu/[*]")
        if self.options.get_safe("with_png"):
            self.requires("libpng/[~1.6]")
        if self.options.get_safe("with_zlib"):
            self.requires("zlib-ng/[^2.0]")

    def validate(self):
        if self.options.shared and self.options.with_glib and not self.dependencies["glib"].options.shared:
            raise ConanInvalidConfiguration(
                "Linking a shared library against static glib can cause unexpected behaviour."
            )
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "7":
            raise ConanInvalidConfiguration("New versions of harfbuzz require at least gcc 7")

        if self.options.with_glib and self.dependencies["glib"].options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration(
                "Linking shared glib with the MSVC static runtime is not supported"
            )

        if self.options.with_introspection and not self.options.shared:
            raise ConanInvalidConfiguration("with_introspection=True requires -o shared=True")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.with_glib:
            self.tool_requires("glib/<host_version>")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "meson.build", "subdir('util')", "")

    def generate(self):
        def is_enabled(value):
            return "enabled" if value else "disabled"

        def meson_backend_and_flags():
            if is_msvc(self) and self.settings.compiler.version == "191" and self.settings.build_type == "Debug":
                # Mitigate https://learn.microsoft.com/en-us/cpp/build/reference/zf?view=msvc-170
                return "vs", ["/bigobj"]
            return "ninja", []

        # Avoid conflicts with libiconv
        # see: https://github.com/conan-io/conan-center-index/pull/17046#issuecomment-1554629094
        if self.settings_build.os == "Macos":
            env = Environment()
            env.define_path("DYLD_FALLBACK_LIBRARY_PATH", "$DYLD_LIBRARY_PATH")
            env.define_path("DYLD_LIBRARY_PATH", "")
            env.vars(self, scope="build").save_script("conanbuild_macos_runtimepath")

        deps = PkgConfigDeps(self)
        deps.generate()

        backend, cxxflags = meson_backend_and_flags()
        tc = MesonToolchain(self, backend=backend)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["glib"] = is_enabled(self.options.with_glib)
        tc.project_options["gobject"] = is_enabled(self.options.with_glib)
        tc.project_options["cairo"] = "disabled"  # TODO
        tc.project_options["chafa"] = "disabled"  # TODO
        tc.project_options["icu"] = is_enabled(self.options.with_icu)
        tc.project_options["graphite2"] = "disabled"  # TODO
        tc.project_options["freetype"] = is_enabled(self.options.with_freetype)
        if Version(self.version) >= "9.0.0":
            tc.project_options["fontations"] = "disabled"  # TODO
        if Version(self.version) >= "14.0.0":
            # harfbuzz-subset has always been part of this package and is
            # represented by the `subset` Conan component below.
            tc.project_options["subset"] = "enabled"
            tc.project_options["png"] = is_enabled(self.options.with_png)
            tc.project_options["zlib"] = is_enabled(self.options.with_zlib)
            tc.project_options["raster"] = is_enabled(self.options.with_raster)
            tc.project_options["vector"] = is_enabled(self.options.with_vector)
            tc.project_options["gpu"] = is_enabled(self.options.with_gpu)
            tc.project_options["gpu_demo"] = "disabled"
        tc.project_options["gdi"] = is_enabled(self.options.get_safe("with_gdi"))
        tc.project_options["directwrite"] = is_enabled(self.options.get_safe("with_directwrite"))
        tc.project_options["coretext"] = is_enabled(self.options.get_safe("with_coretext"))
        tc.project_options["introspection"] = is_enabled(self.options.with_introspection)
        tc.project_options["tests"] = "disabled"
        tc.project_options["docs"] = "disabled"
        tc.project_options["benchmark"] = "disabled"
        tc.project_options["icu_builtin"] = "false"
        tc.cpp_args += cxxflags
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "harfbuzz")
        self.cpp_info.set_property("pkg_config_name", "_harfbuzz-do-not-use")

        self.cpp_info.components["harfbuzz_"].set_property("cmake_target_name", "harfbuzz::harfbuzz")
        self.cpp_info.components["harfbuzz_"].set_property("pkg_config_name", "harfbuzz")
        self.cpp_info.components["harfbuzz_"].libs = ["harfbuzz"]
        self.cpp_info.components["harfbuzz_"].includedirs.append(os.path.join("include", "harfbuzz"))
        if self.options.with_freetype:
            self.cpp_info.components["harfbuzz_"].requires.append("freetype::freetype")
        if self.options.with_glib:
            self.cpp_info.components["harfbuzz_"].requires.append("glib::glib-2.0")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["harfbuzz_"].system_libs.extend(["m", "pthread"])
        if self.settings.os == "Windows" and not self.options.shared:
            self.cpp_info.components["harfbuzz_"].system_libs.append("user32")
            if self.options.with_gdi or self.options.with_uniscribe:
                self.cpp_info.components["harfbuzz_"].system_libs.append("gdi32")
            if self.options.with_uniscribe or self.options.with_directwrite:
                self.cpp_info.components["harfbuzz_"].system_libs.append("rpcrt4")
            if self.options.with_uniscribe:
                self.cpp_info.components["harfbuzz_"].system_libs.append("usp10")
            if self.options.with_directwrite:
                self.cpp_info.components["harfbuzz_"].system_libs.append("dwrite")
        if is_apple_os(self) and self.options.get_safe("with_coretext", False):
            if self.settings.os == "Macos":
                self.cpp_info.components["harfbuzz_"].frameworks.append("ApplicationServices")
            else:
                self.cpp_info.components["harfbuzz_"].frameworks.extend(["CoreFoundation", "CoreGraphics", "CoreText"])
        if not self.options.shared:
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.components["harfbuzz_"].system_libs.append(libcxx)

        if self.options.with_introspection:
            self.cpp_info.components["harfbuzz_"].resdirs = ["share"]
            self.cpp_info.components["harfbuzz_"].requires.extend(["gobject-introspection::gobject-introspection", "glib-gir::glib-gir"])
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))

        self.cpp_info.components["subset"].set_property("cmake_target_name", "harfbuzz::subset")
        self.cpp_info.components["subset"].set_property("pkg_config_name", "harfbuzz-subset")
        self.cpp_info.components["subset"].libs = ["harfbuzz-subset"]
        self.cpp_info.components["subset"].requires = ["harfbuzz_"]

        if self.options.get_safe("with_raster"):
            self.cpp_info.components["raster"].set_property("cmake_target_name", "harfbuzz::raster")
            self.cpp_info.components["raster"].set_property("pkg_config_name", "harfbuzz-raster")
            self.cpp_info.components["raster"].libs = ["harfbuzz-raster"]
            self.cpp_info.components["raster"].requires = ["harfbuzz_"]
            if self.options.with_png:
                self.cpp_info.components["raster"].requires.append("libpng::libpng")

        if self.options.get_safe("with_vector"):
            self.cpp_info.components["vector"].set_property("cmake_target_name", "harfbuzz::vector")
            self.cpp_info.components["vector"].set_property("pkg_config_name", "harfbuzz-vector")
            self.cpp_info.components["vector"].libs = ["harfbuzz-vector"]
            self.cpp_info.components["vector"].requires = ["harfbuzz_"]
            if self.options.with_zlib:
                self.cpp_info.components["vector"].requires.append("zlib-ng::zlib-ng")

        if self.options.get_safe("with_gpu"):
            self.cpp_info.components["gpu"].set_property("cmake_target_name", "harfbuzz::gpu")
            self.cpp_info.components["gpu"].set_property("pkg_config_name", "harfbuzz-gpu")
            self.cpp_info.components["gpu"].libs = ["harfbuzz-gpu"]
            self.cpp_info.components["gpu"].requires = ["harfbuzz_"]

        if self.options.with_icu:
            self.cpp_info.components["icu"].set_property("cmake_target_name", "harfbuzz::icu")
            self.cpp_info.components["icu"].set_property("pkg_config_name", "harfbuzz-icu")
            self.cpp_info.components["icu"].libs = ["harfbuzz-icu"]
            self.cpp_info.components["icu"].requires = ["harfbuzz_", "icu::icu-uc"]

        if self.options.with_glib:
            self.cpp_info.components["gobject"].set_property("cmake_target_name", "harfbuzz::gobject")
            self.cpp_info.components["gobject"].set_property("pkg_config_name", "harfbuzz-gobject")
            self.cpp_info.components["gobject"].libs = ["harfbuzz-gobject"]
            self.cpp_info.components["gobject"].requires = ["harfbuzz_", "glib::glib-2.0", "glib::gobject-2.0"]
