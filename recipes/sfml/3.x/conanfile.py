import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime

required_conan_version = ">=2.1"


class SfmlConan(ConanFile):
    name = "sfml"
    description = "Simple and Fast Multimedia Library."
    license = "Zlib"
    homepage = "https://www.sfml-dev.org"
    topics = ("multimedia", "games", "graphics", "audio")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "window": [True, False],
        "graphics": [True, False],
        "network": [True, False],
        "audio": [True, False],
        "drm": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "window": True,
        "graphics": True,
        "network": True,
        "audio": True,
        "drm": False,
        "mbedtls/*:enable_threading": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os != "Linux":
            self.options.rm_safe("drm")

    def configure(self):
        if not self.options.window:
            self.options.rm_safe("drm")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.window:
            if self.settings.os in ["Windows", "Linux", "FreeBSD", "Macos"]:
                self.requires("opengl/system")
            if self.settings.os == "Linux":
                self.requires("libudev/[>=255 <system]")
                if self.options.drm:
                    self.requires("libdrm/[~2.4.126]")
                    self.requires("gbm/system")
                    self.requires("egl/system")
                else:
                    self.requires("xorg/system")
            elif self.settings.os == "FreeBSD":
                self.requires("xorg/system")
        if self.options.graphics:
            self.requires("freetype/[^2.13.3]")
            self.requires("harfbuzz/[>=11.4.1 <15]")
            self.requires("sheenbidi/[^3.0.0]")
        if self.options.audio:
            self.requires("flac/[^1.5.0]")
            self.requires("vorbis/[^1.3.7]")
        if self.options.network:
            self.requires("mbedtls/[^3.6.4]")
            self.requires("libssh2/[^1.11.1]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.28 <5]")

    def validate(self):
        if self.settings.os not in ["Windows", "Linux", "FreeBSD", "Android", "Macos", "iOS"]:
            raise ConanInvalidConfiguration(f"{self.ref} not supported on {self.settings.os}")
        if self.options.graphics and not self.options.window:
            raise ConanInvalidConfiguration("sfml:graphics=True requires sfml:window=True")
        if self.settings.os == "Windows" and self.options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration("SFML shared libraries require the MSVC dynamic runtime")
        if self.settings.os == "Windows" and self.options.network:
            raise ConanInvalidConfiguration(
                "sfml:network=True requires a thread-enabled mbedtls package, which RoboConan does not support on Windows"
            )

        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["SFML_BUILD_WINDOW"] = self.options.window
        tc.cache_variables["SFML_BUILD_GRAPHICS"] = self.options.graphics
        tc.cache_variables["SFML_BUILD_NETWORK"] = self.options.network
        tc.cache_variables["SFML_BUILD_AUDIO"] = self.options.audio
        tc.cache_variables["SFML_USE_SYSTEM_DEPS"] = True
        tc.cache_variables["SFML_BUILD_FRAMEWORKS"] = False
        tc.cache_variables["SFML_INSTALL_PKGCONFIG_FILES"] = False
        tc.cache_variables["SFML_CONFIGURE_EXTRAS"] = False
        tc.cache_variables["SFML_GENERATE_PDB"] = False
        tc.cache_variables["SFML_ENABLE_PCH"] = False
        tc.cache_variables["SFML_ENABLE_SANITIZERS"] = False
        tc.cache_variables["SFML_ENABLE_STDLIB_ASSERTIONS"] = False
        tc.cache_variables["SFML_OPENGL_ES"] = self.settings.os in ["Android", "iOS"]
        if self.settings.os == "Linux" and self.options.window:
            tc.cache_variables["SFML_USE_DRM"] = self.options.drm
        if is_msvc(self):
            tc.cache_variables["SFML_USE_STATIC_STD_LIBS"] = is_msvc_static_runtime(self)
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.graphics:
            deps.set_property("harfbuzz", "cmake_file_name", "HarfBuzz")
            deps.set_property("harfbuzz::harfbuzz_", "cmake_target_name", "HarfBuzz::HarfBuzz")
        if self.options.audio:
            deps.set_property("flac", "cmake_file_name", "FLAC")
        if self.options.network:
            deps.set_property("mbedtls::libembedtls", "cmake_target_name", "mbedtls")
            deps.set_property("mbedtls::mbedx509", "cmake_target_name", "mbedx509")
            deps.set_property("mbedtls::mbedcrypto", "cmake_target_name", "mbedcrypto")
            deps.set_property("libssh2", "cmake_target_name", "libssh2::libssh2")
        if self.settings.os == "Linux" and self.options.window and self.options.drm:
            deps.set_property("libdrm", "cmake_file_name", "DRM")
            deps.set_property("libdrm::libdrm_libdrm", "cmake_target_name", "DRM::DRM")
            deps.set_property("gbm", "cmake_file_name", "GBM")
            deps.set_property("gbm", "cmake_target_name", "GBM::GBM")
            deps.set_property("egl", "cmake_file_name", "EGL")
            deps.set_property("egl", "cmake_target_name", "EGL::EGL")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "license.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    @property
    def _library_suffix(self):
        if self.options.shared:
            return "-d" if self.settings.build_type == "Debug" else ""
        return "-s-d" if self.settings.build_type == "Debug" else "-s"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SFML")
        if all((self.options.window, self.options.graphics, self.options.network, self.options.audio)):
            self.cpp_info.set_property("pkg_config_name", "sfml-all")
        defines = [] if self.options.shared else ["SFML_STATIC"]

        system = self.cpp_info.components["system"]
        system.set_property("cmake_target_name", "SFML::System")
        system.set_property("pkg_config_name", "sfml-system")
        system.libs = [f"sfml-system{self._library_suffix}"]
        system.defines = defines
        if self.settings.os == "Linux":
            system.system_libs = ["pthread", "rt"]
        elif self.settings.os == "Windows":
            system.system_libs = ["winmm"]
        elif self.settings.os == "Android":
            system.system_libs = ["android", "log"]
        elif self.settings.os == "FreeBSD":
            system.system_libs = ["pthread"]

        if self.settings.os in ["Windows", "Android", "iOS"]:
            main = self.cpp_info.components["main"]
            main.set_property("cmake_target_name", "SFML::Main")
            main.libs = ["sfml-main-d" if self.settings.build_type == "Debug" else "sfml-main"]
            main.defines = defines
            if self.settings.os == "Android":
                main.requires = ["system"]
                main.system_libs = ["android"]
                main.exelinkflags = ["LINKER:-u,ANativeActivity_onCreate"]
                main.sharedlinkflags = ["LINKER:-u,ANativeActivity_onCreate"]
            elif self.settings.os == "iOS":
                main.requires = ["window"]

        if self.options.window:
            window = self.cpp_info.components["window"]
            window.set_property("cmake_target_name", "SFML::Window")
            window.set_property("pkg_config_name", "sfml-window")
            window.libs = [f"sfml-window{self._library_suffix}"]
            window.defines = defines
            window.requires = ["system"]
            if self.settings.os in ["Windows", "Linux", "FreeBSD", "Macos"]:
                window.requires.append("opengl::opengl")
            if self.settings.os == "Linux":
                window.requires.append("libudev::libudev")
                if self.options.drm:
                    window.requires.extend(["libdrm::libdrm_libdrm", "gbm::gbm", "egl::egl"])
                else:
                    window.requires.extend(["xorg::x11", "xorg::xrandr", "xorg::xcursor", "xorg::xi"])
            elif self.settings.os == "FreeBSD":
                window.requires.extend(["xorg::x11", "xorg::xrandr", "xorg::xcursor", "xorg::xi"])
            if self.settings.os == "Windows":
                window.system_libs = ["gdi32", "winmm"]
            elif self.settings.os == "Linux":
                window.system_libs = ["dl"]
            elif self.settings.os == "FreeBSD":
                window.system_libs = ["usbhid"]
            elif self.settings.os == "Android":
                window.system_libs = ["android", "EGL", "GLESv1_CM"]
            if self.settings.os == "Macos":
                window.frameworks = ["Foundation", "AppKit", "IOKit", "Carbon"]
                if not self.options.shared:
                    window.exelinkflags = ["-ObjC"]
                    window.sharedlinkflags = ["-ObjC"]
            elif self.settings.os == "iOS":
                window.frameworks = ["Foundation", "UIKit", "CoreGraphics", "QuartzCore", "CoreMotion", "OpenGLES"]

        if self.options.graphics:
            graphics = self.cpp_info.components["graphics"]
            graphics.set_property("cmake_target_name", "SFML::Graphics")
            graphics.set_property("pkg_config_name", "sfml-graphics")
            graphics.libs = [f"sfml-graphics{self._library_suffix}"]
            graphics.defines = defines
            graphics.requires = [
                "window",
                "freetype::freetype",
                "harfbuzz::harfbuzz_",
                "sheenbidi::sheenbidi",
            ]
        if self.options.network:
            network = self.cpp_info.components["network"]
            network.set_property("cmake_target_name", "SFML::Network")
            network.set_property("pkg_config_name", "sfml-network")
            network.libs = [f"sfml-network{self._library_suffix}"]
            network.defines = defines
            network.requires = ["system", "libssh2::libssh2", "mbedtls::libembedtls"]
            if self.settings.os == "Windows":
                network.system_libs = ["crypt32", "ws2_32", "dnsapi"]
            elif self.settings.os in ["Linux", "Macos", "iOS"]:
                network.system_libs = ["resolv"]
            if self.settings.os == "Macos":
                network.frameworks = ["Security", "CoreFoundation"]

        if self.options.audio:
            audio = self.cpp_info.components["audio"]
            audio.set_property("cmake_target_name", "SFML::Audio")
            audio.set_property("pkg_config_name", "sfml-audio")
            audio.libs = [f"sfml-audio{self._library_suffix}"]
            audio.defines = defines
            audio.requires = [
                "system",
                "flac::libflac",
                "vorbis::vorbismain",
                "vorbis::vorbisfile",
                "vorbis::vorbisenc",
            ]
            if self.settings.os == "Linux":
                audio.system_libs = ["dl"]
            elif self.settings.os == "Android":
                audio.system_libs = ["android", "OpenSLES"]
            elif is_apple_os(self):
                audio.frameworks = ["Foundation", "CoreFoundation", "CoreAudio", "AudioToolbox", "AVFoundation"]
