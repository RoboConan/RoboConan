import os
import platform
import textwrap
from collections import defaultdict
from functools import cached_property
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building, check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv, Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class QtConan(ConanFile):
    name = "qt"
    description = "Qt is a cross-platform framework for graphical user interfaces."
    topics = ("framework", "ui")
    homepage = "https://www.qt.io"
    license = "LGPL-3.0-only"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],

        "opengl": ["no", "desktop", "dynamic"],
        "with_vulkan": [True, False],
        "openssl": [True, False],
        "with_pcre2": [True, False],
        "with_glib": [True, False],
        "with_doubleconversion": [True, False],
        "with_freetype": [True, False],
        "with_fontconfig": [True, False],
        "with_icu": [True, False],
        "with_harfbuzz": [True, False],
        "with_libb2": [True, False],
        "with_jasper": [True, False],
        "with_libjpeg": [True, False],
        "with_libpng": [True, False],
        "with_libtiff": [True, False],
        "with_libwebp": [True, False],
        "with_sqlite3": [True, False],
        "with_mysql": [True, False],
        "with_pq": [True, False],
        "with_odbc": [True, False],
        "with_zstd": [True, False],
        "with_brotli": [True, False],
        "with_dbus": [True, False],
        "with_libalsa": [True, False],
        "with_openal": [True, False],
        "with_gstreamer": [True, False],
        "with_pulseaudio": [True, False],
        "with_gssapi": [True, False],
        "with_md4c": [True, False],
        "with_x11": [True, False],
        "with_egl": [True, False],

        "gui": [True, False],
        "widgets": [True, False],

        "unity_build": [True, False],
        "device": [None, "ANY"],
        "disabled_features": [None, "ANY"],
        "force_build_tools": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,

        "opengl": "desktop",
        "with_vulkan": False,
        "openssl": True,
        "with_pcre2": True,
        "with_glib": False,
        "with_doubleconversion": True,
        "with_freetype": True,
        "with_fontconfig": True,
        "with_icu": True,
        "with_harfbuzz": True,
        "with_libb2": False,
        "with_jasper": True,
        "with_libjpeg": True,
        "with_libpng": True,
        "with_libtiff": True,
        "with_libwebp": True,
        "with_sqlite3": True,
        "with_mysql": False,
        "with_pq": False,
        "with_odbc": False,
        "with_zstd": True,
        "with_brotli": True,
        "with_dbus": False,
        "with_libalsa": False,
        "with_openal": True,
        "with_gstreamer": False,
        "with_pulseaudio": False,
        "with_gssapi": False,
        "with_md4c": True,
        "with_x11": True,
        "with_egl": False,

        "gui": True,
        "widgets": True,

        "unity_build": False,
        "device": None,
        "disabled_features": "",
        "force_build_tools": False,
    }
    # All submodules are exposed as options as well
    _modules = [
        "qt3d",
        "qt5compat",
        "qtactiveqt",
        "qtcharts",
        "qtcoap",
        "qtconnectivity",
        "qtdatavis3d",
        "qtdeclarative",
        "qtdoc",
        "qtgraphs",
        "qtgrpc",
        "qthttpserver",
        "qtimageformats",
        "qtlanguageserver",
        "qtlocation",
        "qtlottie",
        "qtmqtt",
        "qtmultimedia",
        "qtnetworkauth",
        "qtopcua",
        "qtpositioning",
        "qtquick3d",
        "qtquick3dphysics",
        "qtquickeffectmaker",
        "qtquicktimeline",
        "qtremoteobjects",
        "qtscxml",
        "qtsensors",
        "qtserialbus",
        "qtserialport",
        "qtshadertools",
        "qtspeech",
        "qtsvg",
        "qttools",
        "qttranslations",
        "qtvirtualkeyboard",
        "qtwayland",
        "qtwebchannel",
        "qtwebengine",
        "qtwebsockets",
        "qtwebview",
    ]
    options.update({module: ["auto", True, False] for module in _modules})
    default_options.update({module: "auto" for module in _modules})
    # essential_modules, addon_modules, deprecated_modules, preview_modules:
    #    these are only provided for convenience, set to False by default
    _module_statuses = ["essential", "addon", "deprecated", "preview"]
    options.update({f"{status}_modules": [True, False] for status in _module_statuses})
    default_options.update({f"{status}_modules": False for status in _module_statuses})

    @cached_property
    def _qtmodules_info(self):
        """
        Returns the contents of qtmodules/<version>.conf file as a dict.
        Modules that are always required or marked as 'ignored' are excluded.
        Also checks that all modules in the config are exposed as options.
        """
        modules = _parse_gitmodules_file(Path(self.recipe_folder, "qtmodules", f"{self.version}.conf"))
        for module, info in list(modules.items()):
            if module in ["qtbase", "qtqa", "qtrepotools"] or info["status"] == "ignore":
                del modules[module]
                continue
            assert info["status"] in self._module_statuses, f"module {module} has status {info['status']} which is not in self._module_statuses {self._module_statuses}"
            assert module in self._modules, f"module {module} not in self._submodules"
            info["depends"] = info.get("depends", "").split()
        return modules

    @property
    def _xplatform(self):
        return _qt_xplatform(
            str(self.settings.os),
            str(self.settings.arch),
            str(self.settings.compiler),
            str(self.settings.compiler.version),
            str(self.settings.compiler.get_safe("libcxx")),
        )

    @property
    def _android_abi(self):
        return {
            "armv7": "armeabi-v7a",
            "armv8": "arm64-v8a",
            "x86": "x86",
            "x86_64": "x86_64",
        }.get(str(self.settings.arch))

    def export(self):
        copy(self, f"{self.version}.conf", os.path.join(self.recipe_folder, "qtmodules"), os.path.join(self.export_folder, "qtmodules"))
        copy(self, f"{self.version}.yml", os.path.join(self.recipe_folder, "sources"), os.path.join(self.export_folder, "sources"))
        copy(self, "mirrors.txt", self.recipe_folder, self.export_folder)

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "cmake/*", self.recipe_folder, self.export_sources_folder, keep_path=True)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_icu
            del self.options.with_fontconfig
            del self.options.with_libalsa
            del self.options.with_x11
            del self.options.with_egl
            self.options.with_glib = False
        if self.settings.os == "Windows":
            self.options.opengl = "dynamic"
            del self.options.with_gssapi
        if self.settings.os != "Linux":
            self.options.qtwayland = False
        if not cross_building(self):
            del self.options.force_build_tools

        for module in self._modules:
            if module not in self._qtmodules_info:
                self.output.debug(f"Removing {module} option as it is not in the module tree for this version, or is marked as obsolete or ignore")
                self.options.rm_safe(module)

    @cached_property
    def _enabled_modules(self):
        # Requested modules:
        # - any module for non-removed options that have 'True' value
        # - any enabled via `xxx_modules` that does not have a 'False' value
        enabled_statuses = {status for status in self._module_statuses if self.options.get_safe(f"{status}_modules")}
        modules_enabled_by_status = {module for module, info in self._qtmodules_info.items() if info["status"] in enabled_statuses}
        explicitly_enabled = set()
        explicitly_disabled = set()
        for module in self._modules:
            if str(self.options.get_safe(module)) not in ["None", "auto"]:
                if self.options.get_safe(module):
                    explicitly_enabled.add(module)
                else:
                    explicitly_disabled.add(module)
        requested_modules = (modules_enabled_by_status | explicitly_enabled) - explicitly_disabled
        self.output.info(f"Requested modules for {self.context} context: {sorted(requested_modules)}")
        required_modules = set()
        dependants = defaultdict(list)
        for module in requested_modules:
            for dep in self._qtmodules_info[module]["depends"]:
                required_modules.add(dep)
                dependants[dep].append(module)
        required_modules.discard("qtbase")
        additional = sorted(required_modules - requested_modules)
        if additional:
            self.output.info(f"Additional required modules for {self.context} context: {additional}")
        required_but_disabled = sorted(required_modules & explicitly_disabled)
        if required_but_disabled:
            required_by = set()
            for m in required_but_disabled:
                required_by |= set(dependants[m])
            raise ConanInvalidConfiguration(f"Modules {required_but_disabled} are explicitly disabled for {self.context} context, "
                                            f"but are required by {sorted(required_by)}, enabled by other options")
        return requested_modules | required_modules

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

        updated_values = {}
        for module in self._modules:
            updated_values[module] = module in self._enabled_modules
        defaults = {module: [True, False] for module in self._modules}
        self.options.update(defaults, updated_values)

        if not self.options.gui:
            del self.options.opengl
            del self.options.with_vulkan
            del self.options.with_freetype
            self.options.rm_safe("with_fontconfig")
            del self.options.with_harfbuzz
            del self.options.with_libjpeg
            del self.options.with_libpng
            del self.options.with_md4c
            self.options.rm_safe("with_x11")
            self.options.rm_safe("with_egl")
        if not self.options.get_safe("qtmultimedia"):
            self.options.rm_safe("with_libalsa")
            del self.options.with_openal
            del self.options.with_gstreamer
            del self.options.with_pulseaudio
        if self.settings.os in ("FreeBSD", "Linux") and self.options.get_safe("qtwebengine"):
            self.options.with_fontconfig = True

        if Version(self.version) >= "6.8.0":
            # INT128 support is mandatory since 6.8.0, but this requires GNU extensions when using libstdc++.
            # Force-enable the extensions for this recipe as a workaround.
            # https://github.com/qt/qtbase/commit/7805b3c32f88a5405a4a12b402c93cf6cb5dedc4
            # https://github.com/qt/qtbase/blob/v6.8.0/src/corelib/global/qtypes.cpp#L506-L511
            if self.settings.compiler.get_safe("libcxx") in ["libstdc++", "libstdc++11"]:
                if not "gnu" in str(self.settings.compiler.cppstd):
                    self.settings.compiler.cppstd = f"gnu{self.settings.compiler.cppstd}"

        if not self.options.qtimageformats:
            del self.options.with_jasper
            del self.options.with_libtiff
            del self.options.with_libwebp

    def validate_build(self):
        if self.options.get_safe("qtquickeffectmaker"):
            # https://github.com/qt/qtquickeffectmaker/blob/v6.8.1/CMakeLists.txt#L53
            if cross_building(self):
                raise ConanInvalidConfiguration("Cross-compiling qtquickeffectmaker is not supported")

    def validate(self):
        skip_ci_reason = self.conf.get("user.conancenter:skip_ci_build", check_type=str)
        if skip_ci_reason:
            # Currently failing on CI for gcc11, see conan-io/conan-center-index#13472
            raise ConanInvalidConfiguration(skip_ci_reason)

        if self.context == "host":
            check_min_cppstd(self, 17)

        if self.settings.compiler == "apple-clang" and Version(self.settings.compiler.version) < "12":
            raise ConanInvalidConfiguration("apple-clang >= 12 required by qt >= 6.4.0")

        if self.settings.compiler == "apple-clang" and Version(self.settings.compiler.version) < "13":
            # note: assuming that by now, any xcode 13 is updated to the latest 13.4.1
            # https://bugreports.qt.io/browse/QTBUG-119490
            raise ConanInvalidConfiguration("apple-clang >= 13.1 is required by qt >= 6.6.1 cf QTBUG-119490")

        if Version(self.version) >= "6.8.3":
            if self.settings.compiler == "msvc" and Version(self.settings.compiler.version) < "193":
                raise ConanInvalidConfiguration("Visual Studio 2022 (MSVC 1930 or newer) is required by qt >= 6.8.3")

            if self.settings.compiler == "apple-clang" and Version(self.settings.compiler.version) < "14":
                raise ConanInvalidConfiguration("apple-clang >= 14 is required by qt >= 6.8.3")

        if self.options.get_safe("qtwebengine"):
            if not self.options.shared:
                raise ConanInvalidConfiguration("Static builds of Qt WebEngine are not supported")
            if not (self.options.gui and self.options.qtdeclarative and self.options.get_safe("qtwebchannel")):
                raise ConanInvalidConfiguration("option qt:qtwebengine requires also qt:gui, qt:qtdeclarative and qt:qtwebchannel")
            if not self.options.with_dbus and self.settings.os == "Linux":
                raise ConanInvalidConfiguration("option qt:webengine requires also qt:with_dbus on Linux")

        if self.options.widgets and not self.options.gui:
            raise ConanInvalidConfiguration("using option qt:widgets without option qt:gui is not possible. "
                                            "You can either disable qt:widgets or enable qt:gui")

        if not self.options.gui:
            for module in [
                "qt3d",
                "qtactiveqt",
                "qtcharts",
                "qtdatavis3d",
                "qtimageformats",
                "qtlottie",
                "qtmultimedia",
                "qtquick3d",
                "qtquick3dphysics",
                "qtquickeffectmaker",
                "qtquicktimeline",
                "qtshadertools",
                "qtvirtualkeyboard",
                "qtwayland",
                "qtwebview",
            ]:
                if self.options.get_safe(module):
                    raise ConanInvalidConfiguration(f"{module} cannot be built without -o qt/*:gui=True")

        if self.settings.os == "Android" and self.options.get_safe("opengl", "no") == "desktop":
            raise ConanInvalidConfiguration("OpenGL desktop is not supported on Android.")

        if self.settings.os != "Windows" and self.options.get_safe("opengl", "no") == "dynamic":
            raise ConanInvalidConfiguration("Dynamic OpenGL is supported only on Windows.")

        if self.options.get_safe("with_fontconfig") and not self.options.get_safe("with_freetype"):
            raise ConanInvalidConfiguration("with_fontconfig cannot be enabled if with_freetype is disabled.")

        if is_msvc_static_runtime(self) and self.options.shared:
            raise ConanInvalidConfiguration("Qt cannot be built as shared library with static runtime")

        if not self.options.with_pcre2:
            # https://bugreports.qt.io/browse/QTBUG-92454
            raise ConanInvalidConfiguration("pcre2 is actually required by qt (QTBUG-92454). please use option qt:with_pcre2=True")

        if self.options.get_safe("with_x11") and not self.dependencies.direct_host["xkbcommon"].options.with_x11:
            raise ConanInvalidConfiguration("The 'with_x11' option for the 'xkbcommon' package must be enabled when the 'with_x11' option is enabled")

        if self.options.get_safe("qtwayland") and not self.dependencies.direct_host["xkbcommon"].options.with_wayland:
            raise ConanInvalidConfiguration("The 'with_wayland' option for the 'xkbcommon' package must be enabled when the 'qtwayland' option is enabled")

        if self.options.with_sqlite3 and not self.dependencies["sqlite3"].options.enable_column_metadata:
            raise ConanInvalidConfiguration("sqlite3 option enable_column_metadata must be enabled for qt")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        if self.info.settings.os == "Android":
            del self.info.options.android_sdk
        for status in self._module_statuses:
            self.info.options.rm_safe(f"{status}_modules")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        if self.options.openssl:
            self.requires("openssl/[>=1.1 <4]")
        if self.options.with_pcre2:
            self.requires("pcre2/[^10.42]")
        if self.options.get_safe("with_vulkan"):
            # Note: the versions of vulkan-loader and moltenvk
            #       must be exactly part of the same Vulkan SDK version
            #       do not update either without checking both
            #       require exactly the same version of vulkan-headers
            self.requires("vulkan-loader/[^1.3.239.0]")
            self.requires("vulkan-headers/[^1.3.239.0]", transitive_headers=True)
            if is_apple_os(self):
                self.requires("moltenvk/1.2.2")
        if self.options.with_glib:
            self.requires("glib/[^2.70.0]")
        if self.options.with_doubleconversion:
            self.requires("double-conversion/[^3.3.0]")
        if self.options.get_safe("with_freetype"):
            self.requires("freetype/[^2.13.2]")
        if self.options.get_safe("with_fontconfig"):
            self.requires("fontconfig/[^2.15.0]")
        if self.options.get_safe("with_icu"):
            self.requires("icu/[*]")
        if self.options.get_safe("with_harfbuzz"):
            self.requires("harfbuzz/[*]")
        if self.options.with_libb2:
            self.requires("libb2/20190723")
        if self.options.get_safe("with_libjpeg"):
            self.requires("libjpeg-meta/latest")
        if self.options.get_safe("with_libpng"):
            self.requires("libpng/[~1.6]")
        if self.options.with_sqlite3:
            self.requires("sqlite3/[>=3.45.0 <4]")
        if self.options.get_safe("with_mysql"):
            self.requires("libmysqlclient/[^8.1.0]")
        if self.options.with_pq:
            self.requires("libpq/[^17.0]")
        if self.options.with_odbc and self.settings.os != "Windows":
            self.requires("odbc/[^2.3.11]")
        if self.options.get_safe("with_openal"):
            self.requires("openal-soft/1.22.2")
        if self.options.get_safe("with_libalsa"):
            self.requires("libalsa/[^1.2.10]")
        if self.options.get_safe("with_x11") or self.options.get_safe("qtwayland"):
            self.requires("xkbcommon/[^1.6.0]")
        if self.options.get_safe("with_x11"):
            self.requires("xorg/system")
        if self.options.get_safe("with_egl"):
            self.requires("egl/system")
        if self.options.get_safe("opengl", "no") != "no" and self.settings.os != "Windows":
            # https://github.com/qt/qtbase/blob/6.8.1/src/gui/opengl/qopengl.h#L105-L118
            self.requires("opengl/system", transitive_headers=True, transitive_libs=True)
        if self.options.with_zstd:
            self.requires("zstd/[~1.5]")
        if self.options.get_safe("qtwayland"):
            self.requires("wayland/[^1.22.0]")
        if self.options.with_brotli:
            self.requires("brotli/[^1.1.0]")
        if self.options.get_safe("qtwebengine") and self.settings.os == "Linux":
            self.requires("expat/[>=2.6.2 <3]")
            self.requires("opus/[^1.4]")
            self.requires("xorg-proto/2024.1")
            self.requires("libxshmfence/1.3")
            self.requires("nss/[^3.93]")
            self.requires("libdrm/[~2.4.119]")
        if self.options.get_safe("with_gstreamer"):
            self.requires("gst-plugins-base/[^1.24]")
        if self.options.get_safe("with_pulseaudio"):
            self.requires("pulseaudio/[^17.0]")
        if self.options.with_dbus:
            self.requires("dbus/[^1.15]")
        if self.options.get_safe("with_gssapi"):
            self.requires("krb5/[^1.21.2]")
        if self.options.get_safe("with_md4c"):
            self.requires("md4c/[^0.5]")

        # https://github.com/qt/qtimageformats/blob/v6.8.3/src/imageformats/configure.cmake
        if self.options.qtimageformats:
            if self.options.with_jasper:
                self.requires("jasper/[^4.2]")
            if self.options.with_libwebp:
                self.requires("libwebp/[^1.3.2]")
            if self.options.with_libtiff:
                self.requires("libtiff/[^4.5]")
            # if self.options.with_libmng:
            #     self.requires("libmng/[^x.x]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.21.1 <5]")
        self.tool_requires("ninja/[^1.10]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.get_safe("qtwebengine"):
            self.tool_requires("gn/qt-6.9.0")
            self.tool_requires("nodejs/18.15.0")
            self.tool_requires("gperf/3.1")
            # gperf, bison, flex, python >= 2.7.5 & < 3
            if self.settings_build.os == "Windows":
                self.tool_requires("winflexbison/[^2.5.25]")
            else:
                self.tool_requires("bison/[^3.8.2]")
                self.tool_requires("flex/[^2.6.4]")
        if self.options.get_safe("qtwayland"):
            self.tool_requires("wayland/<host_version>")
        if cross_building(self):
            need_gui = bool(self._enabled_modules & {
                "qtactiveqt",
                "qtquick3d",
                "qtquick3dphysics",
                "qtquickeffectmaker",
                "qtshadertools",
                "qtwayland",
            })
            self.tool_requires(f"qt/{self.version}", options={
                "gui": self.options.gui and need_gui,
                "widgets": self.options.widgets and need_gui,
                # Make sure all required tools are built
                "qttools": self.options.get_safe("qttools"),
                "qtactiveqt": self.options.get_safe("qtactiveqt"),
                "qtconnectivity": self.options.get_safe("qtconnectivity") and self.options.get_safe("with_bluez", False),
                "qtdeclarative": self.options.qtdeclarative,
                "qtdoc": self.options.qtdoc,
                "qtgrpc": self.options.get_safe("qtgrpc"),
                "qtopcua": self.options.get_safe("qtopcua"),
                "qtquick3d": self.options.get_safe("qtquick3d"),
                "qtquick3dphysics": self.options.get_safe("qtquick3dphysics"),
                "qtquickeffectmaker": self.options.get_safe("qtquickeffectmaker"),
                "qtremoteobjects": self.options.get_safe("qtremoteobjects"),
                "qtscxml": self.options.get_safe("qtscxml"),
                "qtserialbus": self.options.get_safe("qtserialbus"),
                "qtshadertools": self.options.get_safe("qtshadertools"),
                "qtsvg": self.options.get_safe("qtsvg"),
                "qttranslations": self.options.get_safe("qttranslations"),
                "qtwayland": self.options.get_safe("qtwayland"),
                "with_dbus": self.options.with_dbus,
                # Some tools are only built when shared=True
                # https://github.com/qt/qtdeclarative/blob/v6.8.1/tools/CMakeLists.txt#L37
                "shared": self.options.shared,
            })

    def generate(self):
        vbe = VirtualBuildEnv(self)
        vbe.generate()
        if not cross_building(self):
            vre = VirtualRunEnv(self)
            vre.generate(scope="build")

        deps = CMakeDeps(self)
        deps.set_property("libb2", "cmake_file_name", "Libb2")
        deps.set_property("libb2", "cmake_target_name", "Libb2::Libb2")
        deps.set_property("libdrm", "cmake_file_name", "Libdrm")
        deps.set_property("libdrm::libdrm_libdrm", "cmake_target_name", "Libdrm::Libdrm")
        deps.set_property("wayland", "cmake_file_name", "Wayland")
        deps.set_property("wayland::wayland-client", "cmake_target_name", "Wayland::Client")
        deps.set_property("wayland::wayland-server", "cmake_target_name", "Wayland::Server")
        deps.set_property("wayland::wayland-cursor", "cmake_target_name", "Wayland::Cursor")
        deps.set_property("wayland::wayland-egl", "cmake_target_name", "Wayland::Egl")

        # override https://github.com/qt/qtbase/blob/dev/cmake/3rdparty/extra-cmake-modules/find-modules/FindEGL.cmake
        deps.set_property("egl", "cmake_file_name", "EGL")
        deps.set_property("egl", "cmake_find_mode", "module")
        deps.set_property("egl::egl", "cmake_target_name", "EGL::EGL")

        # don't override https://github.com/qt/qtmultimedia/blob/dev/cmake/FindGStreamer.cmake
        deps.set_property("gstreamer", "cmake_file_name", "gstreamer_conan")
        deps.set_property("gstreamer", "cmake_find_mode", "module")

        if cross_building(self) and self.options.get_safe("qtwebengine"):
            # https://github.com/qt/qtwebengine/blob/v6.8.1/src/host/CMakeLists.txt#L22
            deps.build_context_activated = ["qt"]

        deps.generate()

        for f in Path(self.generators_folder).glob("*.cmake"):
            content = f.read_text()
            if " IMPORTED)\n" in content:
                f.write_text(content.replace(" IMPORTED)\n", " IMPORTED GLOBAL)\n"))

        deps = PkgConfigDeps(self)
        deps.generate()

        # Unset potentially conflicting environment variables
        env = Environment()
        env.unset("VCPKG_ROOT")
        if not cross_building(self):
            env.unset("QT_HOST_PATH")
            env.unset("QT_HOST_PATH_CMAKE_DIR")
        env.vars(self).save_script("conanbuildenv_unset_vars")

        # Using ON/OFF to avoid warnings like
        # Auto-resetting 'FEATURE_widgets' from 'TRUE' to 'ON', because the dependent feature 'gui' was marked dirty.
        def _on_off(value):
            return "ON" if value else "OFF"

        tc = CMakeToolchain(self, generator="Ninja")

        tc.absolute_paths = True

        tc.variables["QT_UNITY_BUILD"] = _on_off(self.options.unity_build)

        tc.variables["QT_BUILD_TESTS"] = "OFF"
        tc.variables["QT_BUILD_EXAMPLES"] = "OFF"

        tc.variables["FEATURE_static_runtime"] = _on_off(is_msvc_static_runtime(self))
        tc.variables["FEATURE_optimize_size"] = _on_off(self.settings.build_type == "MinSizeRel")

        for module in self._qtmodules_info:
            tc.variables[f"BUILD_{module}"] = _on_off(self.options.get_safe(module))
        tc.variables["BUILD_qtqa"] = "OFF"
        tc.variables["BUILD_qtrepotools"] = "OFF"

        tc.variables["FEATURE_system_zlib"] = "ON"

        tc.variables["INPUT_opengl"] = self.options.get_safe("opengl", "no")

        # openSSL
        if not self.options.openssl:
            tc.variables["INPUT_openssl"] = "no"
        else:
            tc.variables["HAVE_openssl"] = "ON"
            if self.dependencies["openssl"].options.shared:
                tc.variables["INPUT_openssl"] = "runtime"
                tc.variables["QT_FEATURE_openssl_runtime"] = "ON"
            else:
                tc.variables["INPUT_openssl"] = "linked"
                tc.variables["QT_FEATURE_openssl_linked"] = "ON"

        if self.options.with_dbus:
            tc.variables["INPUT_dbus"] = "linked"
        else:
            tc.variables["FEATURE_dbus"] = "OFF"
        tc.variables["CMAKE_FIND_DEBUG_MODE"] = "FALSE"

        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_WrapZSTD"] = not self.options.with_zstd
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_WrapVulkanHeaders"] = not self.options.get_safe("with_vulkan", False)
        # Prevent finding LibClang from the system
        # this is needed by the QDoc tool inside Qt Tools
        # See: https://github.com/conan-io/conan-center-index/issues/24729#issuecomment-2255291495
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_WrapLibClang"] = True
        # Do not accidentally enable xkbcommon-x11 support when qtwayand is enabled
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_XKB_COMMON_X11"] = not self.options.get_safe("with_x11", False)

        for opt, conf_arg in [
            ("gui", "gui"),
            ("opengl", "opengl"),
            ("widgets", "widgets"),
            ("with_brotli", "brotli"),
            ("with_doubleconversion", "doubleconversion"),
            ("with_egl", "egl"),
            ("with_fontconfig", "fontconfig"),
            ("with_freetype", "freetype"),
            ("with_glib", "glib"),
            ("with_gssapi", "gssapi"),
            ("with_gstreamer", "gstreamer"),
            ("with_harfbuzz", "harfbuzz"),
            ("with_icu", "icu"),
            ("with_jasper", "jasper"),
            ("with_libjpeg", "jpeg"),
            ("with_libmng", "mng"),
            ("with_libpng", "png"),
            ("with_libtiff", "tiff"),
            ("with_libwebp", "webp"),
            ("with_mysql", "sql_mysql"),
            ("with_odbc", "sql_odbc"),
            ("with_pcre2", "pcre2"),
            ("with_pq", "sql_psql"),
            ("with_sqlite3", "sqlite"),
            ("with_vulkan", "vulkan"),
            ("with_x11", "xcb"),
            ("with_x11", "xcb_xlib"),
            ("with_x11", "xkbcommon_x11"),
            ("with_x11", "xlib"),
            ("with_zstd", "zstd"),
        ]:
            tc.variables[f"FEATURE_{conf_arg}"] = _on_off(self.options.get_safe(opt))
            tc.variables[f"FEATURE_system_{conf_arg}"] = _on_off(self.options.get_safe(opt))

        for opt, conf_arg in [
            ("with_doubleconversion", "doubleconversion"),
            ("with_freetype", "freetype"),
            ("with_harfbuzz", "harfbuzz"),
            ("with_libb2", "libb2"),
            ("with_jasper", "jasper"),
            ("with_libjpeg", "libjpeg"),
            ("with_libmng", "mng"),
            ("with_libpng", "libpng"),
            ("with_libtiff", "tiff"),
            ("with_libwebp", "webp"),
            ("with_md4c", "libmd4c"),
            ("with_pcre2", "pcre"),
        ]:
            tc.variables[f"INPUT_{conf_arg}"] = "system" if self.options.get_safe(opt) else "no"

        for feature in str(self.options.disabled_features).split():
            tc.variables[f"FEATURE_{feature}"] = "OFF"

        if self.options.get_safe("qtwebengine"):
            # Use GN from Conan instead of having Qt build it
            tc.variables["Gn_FOUND"] = True
            tc.variables["Gn_VERSION"] = self.version
            gn_dir = self.dependencies.build["gn"].package_folder
            executable = "gn.exe" if self.settings_build.os == "Windows" else "gn"
            tc.variables["Gn_EXECUTABLE"] = os.path.join(gn_dir, "bin", executable).replace("\\", "/")

        if self.settings.os == "Macos":
            tc.variables["FEATURE_framework"] = "OFF"
        elif self.settings.os == "Android":
            tc.variables["CMAKE_ANDROID_NATIVE_API_LEVEL"] = self.settings.os.api_level
            tc.variables["ANDROID_ABI"] = self._android_abi

        if self.options.device:
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = f"devices/{self.options.device}"
        else:
            xplatform_val = self._xplatform
            if xplatform_val:
                tc.variables["QT_QMAKE_TARGET_MKSPEC"] = xplatform_val
            else:
                self.output.warning(f"host not supported: {self.settings.os} {self.settings.compiler} {self.settings.compiler.version} {self.settings.arch}")

        if cross_building(self):
            host_path = self.dependencies.build["qt"].package_folder.replace("\\", "/")
            tc.variables["QT_QMAKE_DEVICE_OPTIONS"] = f"CROSS_COMPILE={host_path}"
            tc.variables["QT_HOST_PATH"] = host_path
            tc.variables["QT_HOST_PATH_CMAKE_DIR"] = f"{host_path}/lib/cmake"
            tc.variables["QT_FORCE_BUILD_TOOLS"] = self.options.force_build_tools

        tc.variables["FEATURE_pkg_config"] = "ON"
        if self.settings.compiler == "gcc" and self.settings.build_type == "Debug" and not self.options.shared:
            tc.variables["BUILD_WITH_PCH"] = "OFF"  # disabling PCH to save disk space

        current_cpp_std = int(str(self.settings.compiler.cppstd).replace("gnu", ""))
        cpp_std_map = {
            11: "FEATURE_cxx11",
            14: "FEATURE_cxx14",
            17: "FEATURE_cxx17",
            20: "FEATURE_cxx20",
            23: "FEATURE_cxx2b",
        }
        for std, feature in cpp_std_map.items():
            tc.variables[feature] = _on_off(current_cpp_std >= std)

        tc.variables["QT_USE_VCPKG"] = False
        tc.cache_variables["QT_USE_VCPKG"] = False

        # TODO: Remove after fixing https://github.com/conan-io/conan/issues/12012
        # Required for several try_compile() tests against Conan packages at
        # https://github.com/qt/qtbase/blob/v6.8.0/src/gui/configure.cmake#L148
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)

        # Fix for a deluge of warnings on CMake 3.31
        #   The VERSION keyword was followed by an empty string or no value at all.
        #   Policy CMP0174 is not set, so cmake_parse_arguments() will unset the
        #   arg_VERSION variable rather than setting it to an empty string.
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0174"] = "OLD"

        tc.generate()

    def source(self):
        pass

    def _get_download_info(self):
        """
        Generate the equivalent of self.conan_data["sources"][self.version] for each enabled module,
        based on sources/<version>.yml and mirrors.txt.
        """
        mirrors = Path(self.recipe_folder, "mirrors.txt").read_text().strip().split()
        archive_info = yaml.safe_load(Path(self.recipe_folder, "sources", f"{self.version}.yml").read_text())
        hashes = archive_info["hashes"]
        # Modules that are not available as source archives and must be downloaded from git instead.
        git_only = archive_info["git_only"]
        # Modules that are no longer stand-alone.
        merged_modules = {"qtquickcontrols2": "qtdeclarative"}

        def _get_module_urls(component):
            version = Version(self.version)
            if component in git_only:
                return [f"https://github.com/qt/{component}/archive/refs/tags/v{version}.tar.gz"]
            return [f"{base_url}qt/{version.major}.{version.minor}/{version}/submodules/{component}-everywhere-src-{version}.tar.xz" for base_url in mirrors]

        def _get_info(component):
            return {
                "url": _get_module_urls(component),
                "sha256": hashes[component],
            }

        download_info = {
            "root": _get_info("qt5"),
            "qtbase": _get_info("qtbase"),
        }
        for module in self._enabled_modules:
            module = merged_modules.get(module, module)
            download_info[module] = _get_info(module)
        return download_info

    def _get_sources(self):
        """
        Equivalent to source(), but downloads only the relevant source archives based on the configuration.
        """
        destination = self.source_folder
        if platform.system() == "Windows":
            # Don't use os.path.join, or it removes the \\?\ prefix, which enables long paths
            destination = rf"\\?\{self.source_folder}"
        download_info = self._get_download_info()
        get(self, **download_info.pop("root"), strip_root=True, destination=destination)
        for component, info in download_info.items():
            self.output.info(f"Fetching {component}...")
            get(self, **info, strip_root=True, destination=os.path.join(destination, component))
        # Remove empty subdirs
        for path in Path(self.source_folder).iterdir():
            if path.is_dir() and not list(path.iterdir()):
                path.rmdir()

    def _patch_sources(self):
        # Exclude patches that are for modules that are not enabled
        patches = []
        for patch in self.conan_data["patches"][self.version]:
            base_path = patch.get("base_path")
            if base_path is None or Path(self.source_folder, patch["base_path"]).is_dir():
                patches.append(patch)
        self.conan_data["patches"][self.version] = patches
        apply_conandata_patches(self)

        for f in ["FindPostgreSQL.cmake"]:
            file = Path(self.source_folder, "qtbase", "cmake", f)
            if file.is_file():
                file.unlink()

        # workaround https://bugreports.qt.io/browse/QTBUG-94356
        if Version(self.version) < "6.8.0":
            replace_in_file(self, os.path.join(self.source_folder, "qtbase", "cmake", "FindWrapSystemZLIB.cmake"), '"-lz"', "ZLIB::ZLIB")
            replace_in_file(self, os.path.join(self.source_folder, "qtbase", "configure.cmake"),
                "set_property(TARGET ZLIB::ZLIB PROPERTY IMPORTED_GLOBAL TRUE)",
                "")

        replace_in_file(self, os.path.join(self.source_folder, "qtbase", "cmake", "QtAutoDetectHelpers.cmake"),
                        "qt_auto_detect_vcpkg()",
                        "# qt_auto_detect_vcpkg()")

        # Handle locating moltenvk headers when vulkan is enabled on macOS
        replace_in_file(self, os.path.join(self.source_folder, "qtbase", "cmake", "FindWrapVulkanHeaders.cmake"),
        "if(APPLE)", "if(APPLE)\n"
                    " find_package(moltenvk REQUIRED QUIET)\n"
                    " target_include_directories(WrapVulkanHeaders::WrapVulkanHeaders INTERFACE ${moltenvk_INCLUDE_DIR})"
        )

        if self.options.get_safe("qtwebengine"):
            for f in ["renderer", os.path.join("renderer", "core"), os.path.join("renderer", "platform")]:
                replace_in_file(self, os.path.join(self.source_folder, "qtwebengine", "src", "3rdparty", "chromium", "third_party", "blink", f, "BUILD.gn"),
                                "  if (enable_precompiled_headers) {\n    if (is_win) {",
                                "  if (enable_precompiled_headers) {\n    if (false) {"
                                )
            # Use GN from Conan
            replace_in_file(self, os.path.join(self.source_folder, "qtwebengine", "configure.cmake"), "find_package(Gn ", "# find_package(Gn ")

    def build(self):
        self._get_sources()
        self._patch_sources()
        if self.settings.os == "Macos":
            save(self, ".qmake.stash", "")
            save(self, ".qmake.super", "")

        enabled = (["gui"] if self.options.gui else []) + (["widgets"] if self.options.widgets else []) + sorted(self._enabled_modules)
        self.output.info(f"Will build the following components for {self.context} context: {enabled}")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _cmake_executables_file(self):
        return os.path.join("lib", "cmake", "Qt6Core", "conan_qt_executables_variables.cmake")

    @property
    def _cmake_cross_compile_targets(self):
        return os.path.join("lib", "cmake", "Qt6Core", "conan_cross_compile_targets.cmake")

    @property
    def _cmake_entry_point_file(self):
        return os.path.join("lib", "cmake", "Qt6Core", "conan_qt_entry_point.cmake")

    def _cmake_qt6_private_file(self, module):
        return os.path.join("lib", "cmake", f"Qt6{module}", f"conan_qt_qt6_{module.lower()}private.cmake")

    @property
    def _built_tools(self):
        if cross_building(self) and not self.options.force_build_tools:
            return []
        targets = ["moc", "rcc", "tracegen", "cmake_automoc_parser", "qlalr", "qmake"]
        if self.options.with_dbus:
            targets.extend(["qdbuscpp2xml", "qdbusxml2cpp"])
        if self.options.gui:
            targets.append("qvkgen")
        if self.options.widgets:
            targets.append("uic")
        if self.settings_build.os == "Macos" and self.settings.os != "iOS":
            targets.extend(["macdeployqt"])
        if self.settings.os == "Windows":
            targets.extend(["windeployqt"])
        if self.options.qttools:
            if self.options.gui:
                targets.extend(["qhelpgenerator"])
            targets.extend(["qtattributionsscanner"])
            targets.extend(["lconvert", "lprodump", "lrelease", "lrelease-pro", "lupdate", "lupdate-pro"])
        if self.options.qtshadertools and self.options.gui:
            targets.append("qsb")
        if self.options.qtdeclarative:
            targets.extend(["qmltyperegistrar", "qmlcachegen", "qmllint", "qmlimportscanner"])
            targets.extend(["qmlformat", "qml", "qmlprofiler", "qmlpreview"])
            if Version(self.version) >= "6.8.0":
                targets.append("qmlaotstats")
            # Note: consider "qmltestrunner", see https://github.com/conan-io/conan-center-index/issues/24276
        if self.options.get_safe("qtremoteobjects"):
            targets.append("repc")
        if self.options.get_safe("qtscxml"):
            targets.append("qscxmlc")
        return targets

    def package(self):
        package_path = Path(self.package_folder)

        if self.settings.os == "Macos":
            save(self, ".qmake.stash", "")
            save(self, ".qmake.super", "")

        cmake = CMake(self)
        cmake.install()

        copy(self, "*LICENSE*", self.source_folder, package_path.joinpath("licenses"), excludes="qtbase/examples/*")
        for module in set(self._modules) - self._enabled_modules:
            rmdir(self, package_path.joinpath("licenses", module))

        rm(self, "*.pdb*", self.package_folder, recursive=True)

        cmake_dir = package_path.joinpath("lib", "cmake")
        tool_dirs = []
        for path in sorted(list(cmake_dir.rglob("Find*.cmake")) + list(cmake_dir.rglob("*Config.cmake")) + list(cmake_dir.rglob("*-config.cmake"))):
            if path.parent.name.endswith("Tools") or path.parent.name in ["Qt6HostInfo", "Qt6BuildInternals"]:
                tool_dirs.append(path.parent)
                continue
            # Keep tool and host info configs for cross-compilation support.
            self.output.info(f"Removing {path.relative_to(package_path)}")
            path.unlink()
        for path in cmake_dir.iterdir():
            if path in tool_dirs:
                continue
            if path.joinpath(f"{path.name}Macros.cmake").is_file():
                continue
            if any(path.glob("QtPublic*Helpers.cmake")):
                continue
            self.output.info(f"Removing {path.relative_to(package_path)}")
            rmdir(self, path)
        rm(self, "ensure_pro_file.cmake", self.package_folder, recursive=True)
        rm(self, "qt-cmake-private-install.cmake", self.package_folder, recursive=True)
        rmdir(self, package_path.joinpath("lib", "pkgconfig"))

        # Copy
        # - conan_cross_compile_targets.cmake
        # - conan_qt_entry_point.cmake
        copy(self, "cmake/*", self.export_sources_folder, package_path.joinpath("lib", "cmake", "Qt6Core"), keep_path=False)

        # Generate lib/cmake/Qt6Core/conan_qt_executables_variables.cmake
        ver = Version(self.version)
        filecontents = textwrap.dedent("""\
            get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)
            set(QT_CMAKE_EXPORT_NAMESPACE Qt6)
            # Prefer executables from a tool_requires on Qt for cross-compilation support, if available.
            if(DEFINED ENV{QT_TOOLS_PREFIX_DIR})
                set(QT_TOOLS_PREFIX_DIR "$ENV{QT_TOOLS_PREFIX_DIR}")
            else()
                set(QT_TOOLS_PREFIX_DIR "${PACKAGE_PREFIX_DIR}")
            endif()
        """)
        filecontents += f"set(QT_VERSION_MAJOR {ver.major})\n"
        filecontents += f"set(QT_VERSION_MINOR {ver.minor})\n"
        filecontents += f"set(QT_VERSION_PATCH {ver.patch})\n"
        if self.settings.os == "Macos":
            filecontents += 'set(__qt_internal_cmake_apple_support_files_path "${QT_TOOLS_PREFIX_DIR}/lib/cmake/Qt6/macos")\n'
        extension = ".exe" if self.settings.os == "Windows" else ""
        for target in self._built_tools:
            for subdir in ["bin", "lib", "libexec"]:
                exe_path = f"{subdir}/{target}{extension}"
                if package_path.joinpath(exe_path).is_file():
                    break
            else:
                raise ConanException(f"Could not find executable {target}{extension} in {self.package_folder}")
            filecontents += textwrap.dedent(f"""\
                if(NOT TARGET ${{QT_CMAKE_EXPORT_NAMESPACE}}::{target})
                    add_executable(${{QT_CMAKE_EXPORT_NAMESPACE}}::{target} IMPORTED)
                    set_target_properties(${{QT_CMAKE_EXPORT_NAMESPACE}}::{target} PROPERTIES IMPORTED_LOCATION ${{QT_TOOLS_PREFIX_DIR}}/{exe_path})
                endif()
            """)
        filecontents += textwrap.dedent(f"""\
            if(NOT DEFINED QT_DEFAULT_MAJOR_VERSION)
                set(QT_DEFAULT_MAJOR_VERSION {ver.major})
            endif()
        """)
        filecontents += 'set(CMAKE_AUTOMOC_MACRO_NAMES "Q_OBJECT" "Q_GADGET" "Q_GADGET_EXPORT" "Q_NAMESPACE" "Q_NAMESPACE_EXPORT")\n'
        save(self, package_path.joinpath(self._cmake_executables_file), filecontents)

        def _create_private_module(module, dependencies):
            dependencies_string = ";".join(f"Qt6::{dependency}" for dependency in dependencies)
            save(self, package_path.joinpath(self._cmake_qt6_private_file(module)), textwrap.dedent(f"""\
                if(NOT TARGET Qt6::{module}Private)
                    add_library(Qt6::{module}Private INTERFACE IMPORTED)

                    set_target_properties(Qt6::{module}Private PROPERTIES
                        INTERFACE_INCLUDE_DIRECTORIES "${{PACKAGE_PREFIX_DIR}}/include/Qt{module}/{self.version};${{PACKAGE_PREFIX_DIR}}/include/Qt{module}/{self.version}/Qt{module}"
                        INTERFACE_LINK_LIBRARIES "{dependencies_string}"
                    )

                    add_library(Qt::{module}Private INTERFACE IMPORTED)
                    set_target_properties(Qt::{module}Private PROPERTIES
                        INTERFACE_LINK_LIBRARIES "Qt6::{module}Private"
                        _qt_is_versionless_target "TRUE"
                    )
                endif()
            """))

        _create_private_module("Core", ["Core"])

        if self.options.gui:
            _create_private_module("Gui", ["CorePrivate", "Gui"])

        if self.options.widgets:
            _create_private_module("Widgets", ["CorePrivate", "GuiPrivate", "Widgets"])

        if self.options.qtdeclarative:
            _create_private_module("Qml", ["CorePrivate", "Qml"])
            module = package_path.joinpath("lib", "cmake", "Qt6Qml", "conan_qt_qt6_policies.cmake")
            save(self, module, "set(QT_KNOWN_POLICY_QTP0001 TRUE)\n")
            if self.options.gui and self.options.qtshadertools:
                _create_private_module("Quick", ["CorePrivate", "GuiPrivate", "QmlPrivate", "Quick"])

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Qt6")
        self.cpp_info.set_property("pkg_config_name", "qt6")

        # consumers will need the QT_PLUGIN_PATH defined in runenv
        self.runenv_info.define_path("QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins"))
        self.buildenv_info.define_path("QT_PLUGIN_PATH", os.path.join(self.package_folder, "plugins"))

        if not cross_building(self):
            self.buildenv_info.define_path("QT_HOST_PATH", self.package_folder)
            self.buildenv_info.define_path("QT_HOST_PATH_CMAKE_DIR", os.path.join(self.package_folder, "lib", "cmake"))

        # For separate tool_requires on Qt support with Conan.
        # Used in conan_qt_executables_variables.cmake
        if self.context == "build":
            self.buildenv_info.define_path("QT_TOOLS_PREFIX_DIR", self.package_folder.replace("\\", "/"))

        build_modules = {}
        def _add_build_module(component, module):
            assert Path(self.package_folder, module).is_file(), f"Module {module} not found in {self.package_folder}"
            if component not in build_modules:
                build_modules[component] = []
            build_modules[component].append(module)

        libsuffix = ""
        if self.settings.build_type == "Debug":
            if is_msvc(self):
                libsuffix = "d"
            if is_apple_os(self):
                libsuffix = "_debug"

        def _get_corrected_reqs(requires):
            reqs = []
            for req in requires:
                if "::" not in req:
                    req = f"qt{req}"
                    assert req in self.cpp_info.components, f"{req} required but not yet present in self.cpp_info.components"
                reqs.append(req)
            return reqs

        def _create_module(module, requires=None, has_include_dir=True):
            name = f"qt{module}"
            assert name not in self.cpp_info.components, f"Module {module} already present in self.cpp_info.components"
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", f"Qt6::{module}")
            component.set_property("cmake_target_aliases", [f"Qt::{module}"])
            component.set_property("pkg_config_name", f"Qt6{module}")
            libname = module[:-7] if module.endswith("Private") else module
            component.libs = [f"Qt6{libname}{libsuffix}"]
            if has_include_dir:
                component.includedirs = ["include", os.path.join("include", f"Qt{module}")]
            component.defines = [f"QT_{module.upper()}_LIB"]
            requires = requires or []
            if module != "Core" and "Core" not in requires:
                requires.append("Core")
            component.requires = _get_corrected_reqs(requires)
            return component

        def _create_plugin(pluginname, libname, plugintype, requires=None):
            name = f"qt{pluginname}"
            assert name not in self.cpp_info.components, f"Plugin {pluginname} already present in self.cpp_info.components"
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", f"Qt6::{pluginname}")
            if not self.options.shared:
                component.libs = [libname + libsuffix]
            component.libdirs = [os.path.join("plugins", plugintype)]
            component.includedirs = []
            requires = requires or []
            if "Core" not in requires:
                requires.append("Core")
            component.requires = _get_corrected_reqs(requires)
            return component

        qtPlatform = self.cpp_info.components["qtPlatform"]
        qtPlatform.set_property("cmake_target_name", "Qt6::Platform")
        qtPlatform.includedirs = [os.path.join("mkspecs", self._xplatform)]

        qtCore = _create_module("Core")
        qtCore.set_property("pkg_config_custom_content", "\n".join([
            "bindir=${prefix}/bin",
            "libexecdir=${prefix}/libexec",
            "exec_prefix=${prefix}",
        ]))
        qtCore.builddirs.append(os.path.join("bin"))
        _add_build_module("qtCore", self._cmake_executables_file)
        _add_build_module("qtCore", self._cmake_cross_compile_targets)
        _add_build_module("qtCore", self._cmake_qt6_private_file("Core"))
        if self.settings.os in ["Windows", "iOS"]:
            _add_build_module("qtCore", self._cmake_entry_point_file)
        if is_msvc(self):
            qtCore.cxxflags.append("-permissive-")
            qtCore.cxxflags.append("-Zc:__cplusplus")
        elif self.settings.os != "Windows":
            qtCore.cxxflags.append("-fPIC")
        qtCore.requires.append("zlib-ng::zlib-ng")
        if self.options.with_pcre2:
            qtCore.requires.append("pcre2::pcre2")
        if self.options.with_doubleconversion:
            qtCore.requires.append("double-conversion::double-conversion")
        if self.options.get_safe("with_icu"):
            qtCore.requires.append("icu::icu")
        if self.options.with_zstd:
            qtCore.requires.append("zstd::zstd")
        if self.options.with_glib:
            qtCore.requires.append("glib::glib")
        if self.options.openssl:
            qtCore.requires.append("openssl::openssl") # used by QCryptographicHash
        if self.settings.build_type != "Debug":
            qtCore.defines.append("QT_NO_DEBUG")
        if not self.options.shared:
            if is_msvc(self):
                qtCore.system_libs.append("synchronization")
                qtCore.system_libs.append("runtimeobject")
            if self.settings.os == "Windows":
                # https://github.com/qt/qtbase/blob/v6.8.0/src/corelib/CMakeLists.txt#L527-L541
                qtCore.system_libs.extend([
                    "advapi32", "authz", "kernel32", "netapi32", "ole32", "shell32",
                    "user32", "uuid", "version", "winmm", "ws2_32", "mpr", "userenv",
                ])
            elif is_apple_os(self):
                # https://github.com/qt/qtbase/blob/v6.8.0/src/corelib/CMakeLists.txt#L626-L630
                qtCore.frameworks.extend(["CoreFoundation", "Foundation", "IOKit"])
                if self.settings.os == "Macos":
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/corelib/CMakeLists.txt#L645-L651
                    qtCore.frameworks.extend([
                        "AppKit",
                        "ApplicationServices",
                        "CoreServices",
                        "Security",
                        "DiskArbitration",
                    ])
                else:
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/corelib/CMakeLists.txt#L1052
                    qtCore.frameworks.append("MobileCoreServices")
                if self.settings.os in ["iOS", "tvOS"]:
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/corelib/CMakeLists.txt#L1169
                    qtCore.frameworks.append("UIKit")
                if self.settings.os == "watchOS":
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/corelib/CMakeLists.txt#L1174
                    qtCore.frameworks.append("WatchKit")

        if self.options.qt5compat:
            _create_module("Core5Compat")

        if self.options.gui:
            qtGui = _create_module("Gui")
            _add_build_module("qtGui", self._cmake_qt6_private_file("Gui"))
            if self.options.with_dbus:
                qtGui.requires.append("DBus")
            if self.options.with_freetype:
                qtGui.requires.append("freetype::freetype")
            if self.options.with_libpng:
                qtGui.requires.append("libpng::libpng")
            if self.options.get_safe("with_fontconfig"):
                qtGui.requires.append("fontconfig::fontconfig")
            if self.settings.os in ["Linux", "FreeBSD"]:
                if self.options.get_safe("with_x11"):
                    qtGui.requires.append("xorg::xorg")
                    qtGui.requires.append("xkbcommon::libxkbcommon-x11")
                if self.options.get_safe("qtwayland"):
                    qtGui.requires.append("xkbcommon::libxkbcommon")
                if self.options.get_safe("with_egl"):
                    qtGui.requires.append("egl::egl")
            if self.settings.os != "Windows" and self.options.get_safe("opengl", "no") != "no":
                qtGui.requires.append("opengl::opengl")
            if self.options.get_safe("with_vulkan"):
                qtGui.requires.append("vulkan-loader::vulkan-loader")
                qtGui.requires.append("vulkan-headers::vulkan-headers")
                if is_apple_os(self):
                    qtGui.requires.append("moltenvk::moltenvk")
            if self.options.with_harfbuzz:
                qtGui.requires.append("harfbuzz::harfbuzz")
            if self.options.with_glib:
                qtGui.requires.append("glib::glib")
            if self.options.with_md4c:
                qtGui.requires.append("md4c::md4c")
            if not self.options.shared:
                if self.settings.os == "Windows":
                    # https://github.com/qt/qtbase/blob/v6.6.1/src/gui/CMakeLists.txt#L419-L429
                    qtGui.system_libs += [
                        "advapi32", "gdi32", "ole32", "shell32", "user32",
                        "d3d11", "dxgi", "dxguid"
                    ]
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/gui/CMakeLists.txt#L796
                    qtGui.system_libs.append("d2d1")
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/gui/CMakeLists.txt#L803
                    qtGui.system_libs.append("dwrite")
                    if self.settings.compiler == "gcc":
                        # https://github.com/qt/qtbase/blob/v6.8.0/src/gui/CMakeLists.txt#L813
                        qtGui.system_libs.append("uuid")  # FIXME: should be util-linux-libuuid?
                    # https://github.com/qt/qtbase/blob/v6.6.0/src/gui/CMakeLists.txt#L428
                    qtGui.system_libs.append("d3d12")
                    if Version(self.version) >= "6.7.0":
                        # https://github.com/qt/qtbase/blob/v6.8.0/src/gui/CMakeLists.txt#L430
                        qtGui.system_libs.append("uxtheme")
                    if self.settings.compiler == "gcc":
                        qtGui.system_libs.append("uuid")
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/plugins/platforms/direct2d/CMakeLists.txt#L59-L81
                    qtGui.system_libs += [
                        "advapi32", "d2d1", "d3d11", "dwmapi", "dwrite", "dxgi", "dxguid", "gdi32", "imm32", "ole32",
                        "oleaut32", "setupapi", "shell32", "shlwapi", "user32", "version", "winmm", "winspool",
                        "wtsapi32", "shcore", "comdlg32", "d3d9", "runtimeobject"
                    ]
                elif is_apple_os(self):
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/gui/CMakeLists.txt#L423-L429
                    qtGui.frameworks = ["CoreFoundation", "CoreGraphics", "CoreText", "Foundation", "ImageIO"]
                    if self.options.get_safe("opengl", "no") != "no":
                        # https://github.com/qt/qtbase/commit/2ed63e587eefb246dba9e69aa01fdb2abb2def13
                        qtGui.frameworks.append("AGL")
                    if self.settings.os == "Macos":
                        # https://github.com/qt/qtbase/blob/v6.8.0/src/gui/CMakeLists.txt#L394-L398
                        qtGui.frameworks += ["AppKit", "Carbon"]

            _create_plugin("QGifPlugin", "qgif", "imageformats", ["Gui"])
            _create_plugin("QIcoPlugin", "qico", "imageformats", ["Gui"])
            if self.options.get_safe("with_libjpeg"):
                QJpegPlugin = _create_plugin("QJpegPlugin", "qjpeg", "imageformats", ["Gui"])
                if self.options.with_libjpeg:
                    QJpegPlugin.requires.append("libjpeg-meta::jpeg")
            if self.options.get_safe("with_x11"):
                _create_module("XcbQpaPrivate", ["xkbcommon::libxkbcommon-x11", "xorg::xorg"], has_include_dir=False)
                _create_plugin("QXcbIntegrationPlugin", "qxcb", "platforms", ["Core", "Gui", "XcbQpaPrivate"])
            if self.settings.os == "Windows":
                QWindowsIntegrationPlugin = _create_plugin("QWindowsIntegrationPlugin", "qwindows", "platforms", ["Core", "Gui"])
                if not self.options.shared:
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/plugins/platforms/windows/CMakeLists.txt#L52-L68
                    QWindowsIntegrationPlugin.system_libs += [
                        "advapi32", "dwmapi", "gdi32", "imm32", "ole32", "oleaut32", "setupapi", "shell32", "shlwapi",
                        "user32", "winmm", "winspool", "wtsapi32", "shcore", "comdlg32", "d3d9", "runtimeobject"
                    ]
                # https://github.com/qt/qtbase/commit/65d58e6c41e3c549c89ea4f05a8e467466e79ca3
                if Version(self.version) >= "6.7.0":
                    _create_plugin("QModernWindowsStylePlugin", "qmodernwindowsstyle", "styles", ["Core", "Gui"])
                else:
                    _create_plugin("QWindowsVistaStylePlugin", "qwindowsvistastyle", "styles", ["Core", "Gui"])
            elif self.settings.os == "Android":
                QAndroidIntegrationPlugin = _create_plugin("QAndroidIntegrationPlugin", "qtforandroid", "platforms", ["Core", "Gui"])
                if not self.options.shared:
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/plugins/platforms/android/CMakeLists.txt#L66-L67
                    QAndroidIntegrationPlugin.system_libs = ["android", "jnigraphics"]
            elif self.settings.os == "Macos":
                QCocoaIntegrationPlugin = _create_plugin("QCocoaIntegrationPlugin", "qcocoa", "platforms", ["Core", "Gui"])
                if not self.options.shared:
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/plugins/platforms/cocoa/CMakeLists.txt#L51-L58
                    QCocoaIntegrationPlugin.frameworks = [
                        "AppKit", "Carbon", "CoreServices", "CoreVideo", "IOKit", "IOSurface", "Metal", "QuartzCore"
                    ]
                    if Version(self.version) >= "6.8.0":
                        QCocoaIntegrationPlugin.frameworks.append("UniformTypeIdentifiers")
            elif self.settings.os in ["iOS", "tvOS"]:
                QIOSIntegrationPlugin = _create_plugin("QIOSIntegrationPlugin", "qios", "platforms")
                if not self.options.shared:
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/plugins/platforms/ios/CMakeLists.txt#L51-L56
                    QIOSIntegrationPlugin.frameworks = ["AudioToolbox", "Foundation", "Metal", "QuartzCore", "UIKit", "CoreGraphics"]
                    if self.settings.os != "tvOS":
                        # https://github.com/qt/qtbase/blob/v6.8.0/src/plugins/platforms/ios/CMakeLists.txt#L84-L85
                        QIOSIntegrationPlugin.frameworks += ["UniformTypeIdentifiers", "Photos"]
                        if Version(self.version) < "6.8.0":
                            QIOSIntegrationPlugin.frameworks.append("AssetsLibrary")
            elif self.settings.os == "watchOS":
                _create_plugin("QMinimalIntegrationPlugin", "qminimal", "platforms")
            elif self.settings.os == "Emscripten":
                _create_plugin("QWasmIntegrationPlugin", "qwasm", "platforms", ["Core", "Gui"])

        if self.options.widgets:
            qtWidgets = _create_module("Widgets", ["Gui"])
            _add_build_module("qtWidgets", self._cmake_qt6_private_file("Widgets"))
            if not self.options.shared and self.settings.os == "Windows":
                # https://github.com/qt/qtbase/blob/v6.8.0/src/widgets/CMakeLists.txt#L383-L385
                qtWidgets.system_libs += ["dwmapi", "shell32", "uxtheme"]

        if self.options.gui and self.options.widgets:
            qtPrintSupport = _create_module("PrintSupport", ["Gui", "Widgets"])
            if not self.options.shared:
                if self.settings.os == "Windows":
                    qtPrintSupport.system_libs.extend(["gdi32", "user32", "comdlg32", "winspool"])
                elif is_apple_os(self):
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/printsupport/CMakeLists.txt#L59-L61
                    qtPrintSupport.system_libs.append("cups")
                    qtPrintSupport.frameworks.append("ApplicationServices")

        if self.options.with_dbus:
            qtDBus = _create_module("DBus", ["dbus::dbus"])
            if not self.options.shared and self.settings.os == "Windows":
                # https://github.com/qt/qtbase/blob/v6.8.0/src/dbus/CMakeLists.txt#L73-L79
                qtDBus.system_libs.extend(["advapi32", "netapi32", "user32", "ws2_32"])
        if self.options.with_sqlite3:
            _create_plugin("QSQLiteDriverPlugin", "qsqlite", "sqldrivers", ["sqlite3::sqlite3"])
        if self.options.with_pq:
            _create_plugin("QPSQLDriverPlugin", "qsqlpsql", "sqldrivers", ["libpq::libpq"])
        if self.options.with_odbc:
            QODBCDriverPlugin = _create_plugin("QODBCDriverPlugin", "qsqlodbc", "sqldrivers")
            if self.settings.os == "Windows":
                if not self.options.shared:
                    QODBCDriverPlugin.system_libs.append("odbc32")
            else:
                QODBCDriverPlugin.requires.append("odbc::odbc")

        qtNetwork = _create_module("Network")
        if self.options.openssl:
            qtNetwork.requires.append("openssl::openssl")
        if self.options.with_brotli:
            qtNetwork.requires.append("brotli::brotli")
        if self.settings.os in ["Linux", "FreeBSD"] and self.options.with_gssapi:
            qtNetwork.requires.append("krb5::krb5-gssapi")
        if not self.options.shared:
            if self.settings.os == "Windows":
                # https://github.com/qt/qtbase/blob/v6.8.0/src/network/CMakeLists.txt#L196-L200
                qtNetwork.system_libs.extend(["advapi32", "dnsapi", "iphlpapi", "secur32", "winhttp"])
            elif is_apple_os(self):
                qtNetwork.system_libs.append("resolv")
                if self.options.with_gssapi:
                    # https://github.com/qt/qtbase/blob/v6.8.0/src/network/CMakeLists.txt#L273
                    qtNetwork.frameworks.append("GSS")
                if self.settings.os not in ["iOS", "tvOS"]:
                    qtNetwork.frameworks.append("CoreServices")
                    qtNetwork.frameworks.append("SystemConfiguration")

        _create_module("Sql")
        _create_module("Test")
        _create_module("Concurrent")
        _create_module("Xml")
        if self.options.get_safe("opengl", "no") != "no":
            if self.options.gui:
                _create_module("OpenGL", ["Gui"])
            if self.options.widgets:
                _create_module("OpenGLWidgets", ["OpenGL", "Widgets"])

        # since https://github.com/qt/qtdeclarative/commit/4fb84137f1c0a49d64b8bef66fef8a4384cc2a68
        qt_quick_enabled = self.options.qtdeclarative and self.options.gui and self.options.qtshadertools

        if self.options.qtdeclarative:
            _create_module("Qml", ["Network"])
            _add_build_module("qtQml", self._cmake_qt6_private_file("Qml"))
            _create_module("QmlModels", ["Qml"])
            qtQmlImportScanner = self.cpp_info.components["qtQmlImportScanner"]
            qtQmlImportScanner.set_property("cmake_target_name", "Qt6::QmlImportScanner")
            qtQmlImportScanner.requires = _get_corrected_reqs(["Qml"])
            _create_module("QmlWorkerScript", ["Qml"])
            if qt_quick_enabled:
                _create_module("Quick", ["Gui", "Qml", "QmlModels"])
                _add_build_module("qtQuick", self._cmake_qt6_private_file("Quick"))
                if self.options.widgets:
                    _create_module("QuickWidgets", ["Gui", "Qml", "Quick", "Widgets"])
                _create_module("QuickShapes", ["Gui", "Qml", "Quick"])
                _create_module("QuickTest", ["Test", "Quick"])

        if self.options.qttools and self.options.gui and self.options.widgets:
            qtLinguistTools = self.cpp_info.components["qtLinguistTools"]
            qtLinguistTools.set_property("cmake_target_name", "Qt6::LinguistTools")
            qtUiPlugin = _create_module("UiPlugin", ["Gui", "Widgets"])
            qtUiPlugin.libs = [] # this is a collection of abstract classes, so this is header-only
            qtUiPlugin.libdirs = []
            _create_module("UiTools", ["UiPlugin", "Gui", "Widgets"])
            _create_module("Designer", ["Gui", "UiPlugin", "Widgets", "Xml"])
            _create_module("Help", ["Gui", "Sql", "Widgets"])

        if self.options.qtshadertools and self.options.gui:
            _create_module("ShaderTools", ["Gui"])

        if self.options.qtquick3d and qt_quick_enabled:
            _create_module("Quick3DUtils", ["Gui"])
            _create_module("Quick3DAssetImport", ["Gui", "Qml", "Quick3DUtils"])
            _create_module("Quick3DRuntimeRender", ["Gui", "Quick", "Quick3DAssetImport", "Quick3DUtils", "ShaderTools"])
            _create_module("Quick3D", ["Gui", "Qml", "Quick", "Quick3DRuntimeRender"])

        if self.options.get_safe("qtquickcontrols2") and qt_quick_enabled:
            _create_module("QuickControls2", ["Gui", "Quick"])
            _create_module("QuickTemplates2", ["Gui", "Quick"])

        if self.options.qtsvg and self.options.gui:
            _create_module("Svg", ["Gui"])
            _create_plugin("QSvgIconPlugin", "qsvgicon", "iconengines")
            _create_plugin("QSvgPlugin", "qsvg", "imageformats")
            if self.options.widgets:
                _create_module("SvgWidgets", ["Gui", "Svg", "Widgets"])

        if self.options.qtwayland and self.options.gui:
            _create_module("WaylandClient", ["Gui", "wayland::wayland-client"])
            _create_module("WaylandCompositor", ["Gui", "wayland::wayland-server"])

        if self.options.get_safe("qtactiveqt") and self.settings.os == "Windows":
            _create_module("AxBase", ["Gui", "Widgets"])
            qtAxServer = _create_module("AxServer", ["AxBase"])
            qtAxServer.defines.append("QAXSERVER")
            if not self.options.shared:
                qtAxServer.system_libs.append("shell32")
            _create_module("AxContainer", ["AxBase"])
        if self.options.get_safe("qtcharts"):
            _create_module("Charts", ["Gui", "Widgets"])
        if self.options.get_safe("qtdatavis3d") and qt_quick_enabled:
            _create_module("DataVisualization", ["Gui", "OpenGL", "Qml", "Quick"])
        if self.options.get_safe("qtlottie"):
            _create_module("Bodymovin", ["Gui"])
        if self.options.get_safe("qtscxml"):
            _create_module("StateMachine")
            _create_module("StateMachineQml", ["StateMachine", "Qml"])
            _create_module("Scxml")
            _create_plugin("QScxmlEcmaScriptDataModelPlugin", "qscxmlecmascriptdatamodel", "scxmldatamodel", ["Scxml", "Qml"])
            _create_module("ScxmlQml", ["Scxml", "Qml"])
        if self.options.get_safe("qtvirtualkeyboard") and qt_quick_enabled:
            _create_module("VirtualKeyboard", ["Gui", "Qml", "Quick"])
            _create_plugin("QVirtualKeyboardPlugin", "qtvirtualkeyboardplugin", "platforminputcontexts", ["Gui", "Qml", "VirtualKeyboard"])
            _create_plugin("QtVirtualKeyboardHangulPlugin", "qtvirtualkeyboard_hangul", "virtualkeyboard", ["Gui", "Qml", "VirtualKeyboard"])
            _create_plugin("QtVirtualKeyboardMyScriptPlugin", "qtvirtualkeyboard_myscript", "virtualkeyboard", ["Gui", "Qml", "VirtualKeyboard"])
            _create_plugin("QtVirtualKeyboardThaiPlugin", "qtvirtualkeyboard_thai", "virtualkeyboard", ["Gui", "Qml", "VirtualKeyboard"])
        if self.options.get_safe("qt3d"):
            _create_module("3DCore", ["Gui", "Network"])
            _create_module("3DRender", ["3DCore", "OpenGL"])
            _create_module("3DAnimation", ["3DCore", "3DRender", "Gui"])
            _create_module("3DInput", ["3DCore", "Gui"])
            _create_module("3DLogic", ["3DCore", "Gui"])
            _create_module("3DExtras", ["Gui", "3DCore", "3DInput", "3DLogic", "3DRender"])
            _create_plugin("DefaultGeometryLoaderPlugin", "defaultgeometryloader", "geometryloaders", ["3DCore", "3DRender", "Gui"])
            _create_plugin("fbxGeometryLoaderPlugin", "fbxgeometryloader", "geometryloaders", ["3DCore", "3DRender", "Gui"])
            if qt_quick_enabled:
                _create_module("3DQuick", ["3DCore", "Gui", "Qml", "Quick"])
                _create_module("3DQuickAnimation", ["3DAnimation", "3DCore", "3DQuick", "3DRender", "Gui", "Qml"])
                _create_module("3DQuickExtras", ["3DCore", "3DExtras", "3DInput", "3DQuick", "3DRender", "Gui", "Qml"])
                _create_module("3DQuickInput", ["3DCore", "3DInput", "3DQuick", "Gui", "Qml"])
                _create_module("3DQuickRender", ["3DCore", "3DQuick", "3DRender", "Gui", "Qml"])
                _create_module("3DQuickScene2D", ["3DCore", "3DQuick", "3DRender", "Gui", "Qml"])
        if self.options.get_safe("qtimageformats"):
            # https://github.com/qt/qtimageformats/blob/v6.8.3/src/plugins/imageformats/CMakeLists.txt
            _create_plugin("QTgaPlugin", "qtga", "imageformats", ["Gui"])
            _create_plugin("QWbmpPlugin", "qwbmp", "imageformats", ["Gui"])
            if is_apple_os(self):
                mac_heif_plugin = _create_plugin("QMacHeifPlugin", "qmacheif", "imageformats", ["Gui"])
                mac_heif_plugin.frameworks = ["CoreFoundation", "CoreGraphics", "ImageIO"]
            if self.options.with_pcre2:
                _create_plugin("ICNSPlugin", "qicns", "imageformats", ["Gui"])
            if self.options.with_jasper:
                _create_plugin("QJp2Plugin", "qjp2", "imageformats", ["Gui", "jasper::jasper"])
            elif is_apple_os(self):
                mac_jp2_plugin = _create_plugin("QMacJp2Plugin", "qmacjp2", "imageformats", ["Gui"])
                mac_jp2_plugin.frameworks = ["CoreFoundation", "CoreGraphics", "ImageIO"]
            if self.options.get_safe("with_libmng"):
                _create_plugin("QMngPlugin", "qmng", "imageformats", ["Gui", "libmng::libmng"])
            if self.options.with_libtiff:
                _create_plugin("QTiffPlugin", "qtiff", "imageformats", ["Gui", "libtiff::libtiff"])
            if self.options.with_libwebp:
                _create_plugin("QWebpPlugin", "qwebp", "imageformats", ["Gui", "libwebp::libwebp"])
        if self.options.get_safe("qtnetworkauth"):
            _create_module("NetworkAuth", ["Network"])
        if self.options.get_safe("qtcoap"):
            _create_module("Coap", ["Network"])
        if self.options.get_safe("qtmqtt"):
            _create_module("Mqtt", ["Network"])
        if self.options.get_safe("qtopcua"):
            _create_module("OpcUa", ["Network"])
            _create_plugin("QOpen62541Plugin", "open62541_backend", "opcua", ["Network", "OpcUa"])
            _create_plugin("QUACppPlugin", "uacpp_backend", "opcua", ["Network", "OpcUa"])

        if self.options.get_safe("qtmultimedia"):
            multimedia_reqs = ["Network", "Gui"]
            if self.options.get_safe("with_libalsa"):
                multimedia_reqs.append("libalsa::libalsa")
            if self.options.with_openal:
                multimedia_reqs.append("openal-soft::openal-soft")
            if self.options.get_safe("with_pulseaudio"):
                multimedia_reqs.append("pulseaudio::pulse")
            _create_module("Multimedia", multimedia_reqs)
            _create_module("MultimediaWidgets", ["Multimedia", "Widgets", "Gui"])
            if qt_quick_enabled:
                _create_module("MultimediaQuick", ["Multimedia", "Quick"])
            if self.options.with_gstreamer:
                _create_plugin("QGstreamerMediaPlugin", "gstreamermediaplugin", "multimedia", [
                    "gstreamer::gstreamer",
                    "gst-plugins-base::gst-plugins-base"])

        if self.options.get_safe("qtpositioning"):
            _create_module("Positioning")
            _create_plugin("QGeoPositionInfoSourceFactoryGeoclue2", "qtposition_geoclue2", "position")
            _create_plugin("QGeoPositionInfoSourceFactoryPoll", "qtposition_positionpoll", "position")

        if self.options.get_safe("qtsensors"):
            _create_module("Sensors")
            _create_plugin("genericSensorPlugin", "qtsensors_generic", "sensors")
            _create_plugin("IIOSensorProxySensorPlugin", "qtsensors_iio-sensor-proxy", "sensors")
            if self.settings.os == "Linux":
                _create_plugin("LinuxSensorPlugin", "qtsensors_linuxsys", "sensors")
            _create_plugin("QtSensorGesturePlugin", "qtsensorgestures_plugin", "sensorgestures")
            _create_plugin("QShakeSensorGesturePlugin", "qtsensorgestures_shakeplugin", "sensorgestures")

        if self.options.get_safe("qtconnectivity"):
            _create_module("Bluetooth", ["Network"])
            _create_module("Nfc")

        if self.options.get_safe("qtserialport"):
            _create_module("SerialPort")

        if self.options.get_safe("qtserialbus"):
            _create_module("SerialBus", ["SerialPort"] if self.options.get_safe("qtserialport") else [])
            _create_plugin("PassThruCanBusPlugin", "qtpassthrucanbus", "canbus")
            _create_plugin("PeakCanBusPlugin", "qtpeakcanbus", "canbus")
            _create_plugin("SocketCanBusPlugin", "qtsocketcanbus", "canbus")
            _create_plugin("TinyCanBusPlugin", "qttinycanbus", "canbus")
            _create_plugin("VirtualCanBusPlugin", "qtvirtualcanbus", "canbus")

        if self.options.get_safe("qtwebsockets"):
            _create_module("WebSockets", ["Network"])

        if self.options.get_safe("qtwebchannel"):
            _create_module("WebChannel", ["Qml"])

        if self.options.get_safe("qtwebengine") and qt_quick_enabled:
            qtWebEngineCore = _create_module("WebEngineCore", ["Gui", "Quick", "WebChannel"])
            if self.options.get_safe("qtpositioning"):
                qtWebEngineCore.requires.append("Positioning")
            if self.settings.os == "Linux":
                qtWebEngineCore.requires.extend([
                    "expat::expat", "opus::libopus", "xorg-proto::xorg-proto", "libxshmfence::libxshmfence", "nss::nss", "libdrm::libdrm"
                ])
            _create_module("WebEngineQuick", ["WebEngineCore"])
            _create_module("WebEngineWidgets", ["WebEngineCore", "Quick", "PrintSupport", "Widgets", "Gui", "Network"])

        if self.options.get_safe("qtremoteobjects"):
            _create_module("RemoteObjects")

        if self.options.get_safe("qtwebview"):
            _create_module("WebView", ["Core", "Gui"])

        if self.options.get_safe("qtspeech"):
            _create_module("TextToSpeech")

        if self.options.get_safe("qthttpserver"):
            http_server_deps = ["Core", "Network"]
            if self.options.get_safe("qtwebsockets"):
                http_server_deps.append("WebSockets")
            _create_module("HttpServer", http_server_deps)

        if self.options.get_safe("qtgrpc"):
            _create_module("Protobuf")
            _create_module("Grpc", ["Core", "Protobuf", "Network"])

        if self.settings.os in ["Windows", "iOS"]:
            if self.settings.os == "Windows":
                qtEntryPointImplementation = self.cpp_info.components["qtEntryPointImplementation"]
                qtEntryPointImplementation.set_property("cmake_target_name", "Qt6::EntryPointImplementation")
                qtEntryPointImplementation.libs = [f"Qt6EntryPoint{libsuffix}"]
                if not self.options.shared:
                    qtEntryPointImplementation.system_libs = ["shell32"]

                if self.settings.compiler == "gcc":
                    qtEntryPointMinGW32 = self.cpp_info["qtEntryPointMinGW32"]
                    qtEntryPointMinGW32.set_property("cmake_target_name", "Qt6::EntryPointMinGW32")
                    qtEntryPointMinGW32.requires = ["qtEntryPointImplementation"]
                    if not self.options.shared:
                        qtEntryPointMinGW32.system_libs = ["mingw32"]

            qtEntryPointPrivate = self.cpp_info.components["qtEntryPointPrivate"]
            qtEntryPointPrivate.set_property("cmake_target_name", "Qt6::EntryPointPrivate")
            if self.settings.os == "Windows":
                if self.settings.compiler == "gcc":
                    qtEntryPointPrivate.defines.append("QT_NEEDS_QMAIN")
                    qtEntryPointPrivate.requires.append("qtEntryPointMinGW32")
                else:
                    qtEntryPointPrivate.requires.append("qtEntryPointImplementation")
            if self.settings.os == "iOS":
                qtEntryPointPrivate.exelinkflags.append("-Wl,-e,_qt_main_wrapper")

        for path in sorted(Path("lib", "cmake").iterdir()):
            name = path.name
            component_name = name.replace("Qt6", "qt")
            if component_name == "qt":
                component_name = "qtCore"

            if component_name in self.cpp_info.components:
                module = path.joinpath(f"{name}Macros.cmake")
                if module.is_file():
                    _add_build_module(component_name, str(module))
                module = path.joinpath(f"{name}ConfigExtras.cmake")
                if module.is_file():
                    _add_build_module(component_name, str(module))
                for helper_modules in path.glob("QtPublic*Helpers.cmake"):
                    _add_build_module(component_name, str(helper_modules))
                self.cpp_info.components[component_name].builddirs.append(str(path))

            elif component_name.endswith("Tools") and component_name[:-5] in self.cpp_info.components:
                module = path.joinpath(f"{name[:-5]}Macros.cmake")
                if module.is_file():
                    _add_build_module(component_name[:-5], module)
                self.cpp_info.components[component_name[:-5]].builddirs.append(str(path))

        for object_dir in Path(self.package_folder, "lib").glob("objects-*/"):
            for path in sorted(object_dir.iterdir()):
                component = "qt" + path.name.split("_")[0]
                if component in self.cpp_info.components:
                    for root, _, files in os.walk(path):
                        obj_files = [os.path.join(root, file) for file in files]
                        self.cpp_info.components[component].exelinkflags.extend(obj_files)
                        self.cpp_info.components[component].sharedlinkflags.extend(obj_files)

        build_modules_list = []

        if self.options.qtdeclarative:
            build_modules_list.append(os.path.join(self.package_folder, "lib", "cmake", "Qt6Qml", "conan_qt_qt6_policies.cmake"))

        def _add_build_modules_for_component(component):
            for req in self.cpp_info.components[component].requires:
                if "::" not in req:
                    _add_build_modules_for_component(req)
            build_modules_list.extend(build_modules.pop(component, []))

        for c in list(self.cpp_info.components):
            _add_build_modules_for_component(c)

        self.cpp_info.set_property("cmake_build_modules", build_modules_list)

        self.conf_info.define("user.qt:tools_directory", os.path.join(self.package_folder, "bin" if self.settings.os == "Windows" else "libexec"))


def _parse_gitmodules_file(qtmodules_path):
    """A simple parser for the qtmodules/<version>.conf files."""
    submodules = defaultdict(dict)
    current_module = None
    for line in Path(qtmodules_path).read_text().splitlines():
        if line.startswith("[submodule"):
            current_module = line.split('"')[1]
        elif "=" in line:
            key, value = line.split("=", 1)
            submodules[current_module][key.strip()] = value.strip()
    return dict(submodules)

def _qt_xplatform(os, arch, compiler, compiler_version, libcxx):
    if os == "Linux":
        if compiler == "gcc":
            return {
                "x86": "linux-g++-32",
                "armv6": "linux-arm-gnueabi-g++",
                "armv7": "linux-arm-gnueabi-g++",
                "armv7hf": "linux-arm-gnueabi-g++",
                "armv8": "linux-aarch64-gnu-g++",
            }.get(arch, "linux-g++")
        if compiler == "clang":
            if arch == "x86":
                return "linux-clang-libc++-32" if libcxx == "libc++" else "linux-clang-32"
            if arch == "x86_64":
                return "linux-clang-libc++" if libcxx == "libc++" else "linux-clang"
    elif os == "Macos":
        return {
            "clang": "macx-clang",
            "apple-clang": "macx-clang",
            "gcc": "macx-g++",
        }.get(compiler)
    elif os == "iOS":
        if compiler == "apple-clang":
            return "macx-ios-clang"
    elif os == "watchOS":
        if compiler == "apple-clang":
            return "macx-watchos-clang"
    elif os == "tvOS":
        if compiler == "apple-clang":
            return "macx-tvos-clang"
    elif os == "Android":
        if compiler == "clang":
            return "android-clang"
    elif os == "Windows":
        return {
            "msvc": "win32-msvc",
            "gcc": "win32-g++",
            "clang": "win32-clang-g++",
        }.get(compiler)
    elif os == "WindowsStore":
        if compiler == "msvc":
            year = {
                "190": "2015",
                "191": "2017",
                "192": "2019",
            }.get(compiler_version, "2022")
            return {
                "armv7": f"winrt-arm-msvc{year}",
                "x86": f"winrt-x86-msvc{year}",
                "x86_64": f"winrt-x64-msvc{year}",
            }.get(arch)
    elif os == "FreeBSD":
        return {
            "clang": "freebsd-clang",
            "gcc": "freebsd-g++",
        }.get(compiler)
    elif os == "SunOS":
        if compiler == "sun-cc":
            if arch == "sparc":
                return "solaris-cc-stlport" if libcxx == "libstlport" else "solaris-cc"
            if arch == "sparcv9":
                return "solaris-cc64-stlport" if libcxx == "libstlport" else "solaris-cc64"
        elif compiler == "gcc":
            return {
                "sparc": "solaris-g++",
                "sparcv9": "solaris-g++-64",
            }.get(arch)
    elif os == "Neutrino" and compiler == "qcc":
        return {
            "armv8": "qnx-aarch64le-qcc",
            "armv8.3": "qnx-aarch64le-qcc",
            "armv7": "qnx-armle-v7-qcc",
            "armv7hf": "qnx-armle-v7-qcc",
            "armv7s": "qnx-armle-v7-qcc",
            "armv7k": "qnx-armle-v7-qcc",
            "x86": "qnx-x86-qcc",
            "x86_64": "qnx-x86-64-qcc",
        }.get(arch)
    elif os == "Emscripten" and arch == "wasm":
        return "wasm-emscripten"
    return None
