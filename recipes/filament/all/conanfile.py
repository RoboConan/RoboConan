import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, check_max_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class FilamentConan(ConanFile):
    name = "filament"
    description = "Filament is a real-time physically based rendering engine for Android, iOS, Windows, Linux, macOS, and WebGL2"
    license = "Apache-2.0"
    homepage = "https://google.github.io/filament/"
    topics = ("3d-graphics", "android", "webgl", "real-time", "opengl", "metal", "graphics", "vulkan", "wasm", "opengl-es", "pbr", "gltf", "gltf-viewer")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        # Feature options
        "build_fgviewer": [True, False],
        "build_matdbg": [True, False],
        "enable_lto": [True, False],
        "enable_multiview": [True, False],
        "enable_wasm_threads": [True, False],
        "linux_is_mobile": [True, False],
        "use_abseil_logging": [True, False],
        "with_egl": [True, False],
        "with_metal": [True, False],
        "with_opengl": [True, False],
        "with_perfetto": [True, False],
        "with_vulkan": [True, False],
        "with_wayland": [True, False],
        "with_webgpu": [True, False],
        "with_xcb": [True, False],
        "with_xlib": [True, False],
    }
    default_options = {
        "fPIC": True,
        "build_fgviewer": False,
        "build_matdbg": False,
        "enable_lto": False,
        "enable_multiview": False,
        "enable_wasm_threads": False,
        "linux_is_mobile": False,
        "use_abseil_logging": False,
        "with_egl": False,
        "with_metal": True,
        "with_opengl": True,
        "with_perfetto": False,
        "with_vulkan": True,
        "with_wayland": False,
        "with_webgpu": False,
        "with_xcb": True,
        "with_xlib": True,

        "tinyexr/*:header_only": False,
        "glslang/*:install_internal_headers": True,
        "glslang/*:shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if not is_apple_os(self):
            del self.options.with_metal
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_egl
            del self.options.with_wayland
            del self.options.with_xcb
            del self.options.with_xlib
            del self.options.linux_is_mobile
        if self.settings.os != "Android":
            del self.options.with_perfetto
        if self.settings.os != "Emscripten":
            del self.options.enable_wasm_threads
        if self.settings.os in ["Android", "iOS", "Emscripten"]:
            del self.options.with_opengl

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("abseil/[>=20230125]", transitive_headers=True, transitive_libs=True)
        self.requires("libbasisu/[^1.16 <1.50]")
        self.requires("civetweb/[^1.15]")
        # 1.91.5 and newer are not compatible due to https://github.com/ocornut/imgui/commit/191a728ecca454f11ff473e285804d1f7362a83d
        self.requires("imgui/[<1.91.5]")
        self.requires("tsl-robin-map/[^1.2]", transitive_headers=True)
        self.requires("smol-v/[*]")
        self.requires("meshoptimizer/[>=0.20 <1]")
        self.requires("mikktspace/[*]")
        self.requires("cgltf/[^1.13]")
        self.requires("draco/[^1.5]")
        self.requires("stb/[*]")
        self.requires("zstd/[^1.5]")
        self.requires("musl-getopt/[^1]")

        # Host platform dependencies
        if not self._is_mobile_target:
            self.requires("assimp/[^5.3]")
            self.requires("libpng/[^1.6]")
            self.requires("zlib-ng/[^2.0]")
            self.requires("tinyexr/[^1.0]")
            self.requires("jsmn/[^1.1]")

        # SPIRV tools for filamat
        self.requires("glslang/[^1.4.321.0]")
        self.requires("spirv-tools/[^1.4.321.0]")
        self.requires("spirv-cross/[^1.4.321.0]")

        if self.options.get_safe("with_opengl"):
            self.requires("opengl/system", transitive_headers=True)

        if self.options.get_safe("with_egl"):
            self.requires("egl/system", transitive_headers=True)

        # Vulkan dependencies
        if self.options.with_vulkan:
            self.requires("vulkan-memory-allocator/[^3.0]")
            self.requires("spirv-headers/[^1.4.321.0]")

        # Android
        if self.options.get_safe("with_perfetto"):
            self.requires("perfetto/[*]")

        # WebGPU dependencies
        if self.options.with_webgpu:
            self.requires("dawn/[*]")

    def validate(self):
        check_min_cppstd(self, 20)

        if self.settings.compiler not in ["clang", "apple-clang", "msvc"]:
            raise ConanInvalidConfiguration("Filament only supports Clang and MSVC compilers")
        if self.settings.os != "Windows" and self.settings.compiler.libcxx != "libc++":
            raise ConanInvalidConfiguration("Filament requires compiler.libcxx=libc++")

        # Backend validation
        if self.settings.os == "Windows" and not self.options.with_vulkan and not self.options.with_opengl:
            raise ConanInvalidConfiguration("At least one graphics backend must be enabled")
        if is_apple_os(self) and not self.options.with_metal and not self.options.with_opengl:
            raise ConanInvalidConfiguration("Metal or OpenGL backend required on macOS")
        if self.dependencies["glslang"].options.shared:
            raise ConanInvalidConfiguration("glslang can only be used as a static library")

    def validate_build(self):
        # as of v1.65.2:
        #   libs/gltfio/src/AssetLoader.cpp:113:10: error: no member named 'wstring_convert' in namespace 'std'
        check_max_cppstd(self, 23)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.19]")
        if self.options.with_wayland:
            self.tool_requires("wayland/[^1.22.0]")

    @property
    def _is_mobile_target(self):
        return self.settings.os in ["Android", "iOS"] or self.options.linux_is_mobile

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "filament/CMakeLists.txt", "-Werror", "")
        replace_in_file(self, "filament/backend/CMakeLists.txt", "-Werror", "")
        # Do not install in an arch-specific subdir
        replace_in_file(self, "CMakeLists.txt", "set(DIST_DIR", "# set(DIST_DIR")
        # Disable subdirs
        save(self, "filament/test/CMakeLists.txt", "")
        save(self, "filament/benchmark/CMakeLists.txt", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["FILAMENT_SKIP_SAMPLES"] = True
        tc.cache_variables["FILAMENT_BUILD_FILAMAT"] = True  # can't really be disabled
        tc.cache_variables["FILAMENT_ENABLE_FGVIEWER"] = self.options.build_fgviewer
        tc.cache_variables["FILAMENT_ENABLE_LTO"] = self.options.enable_lto
        tc.cache_variables["FILAMENT_ENABLE_MATDBG"] = self.options.build_matdbg
        tc.cache_variables["FILAMENT_ENABLE_MULTIVIEW"] = self.options.enable_multiview
        tc.cache_variables["FILAMENT_ENABLE_PERFETTO"] = self.options.get_safe("with_perfetto", False)
        tc.cache_variables["FILAMENT_LINUX_IS_MOBILE"] = self.options.get_safe("linux_is_mobile", False)
        tc.cache_variables["FILAMENT_SKIP_SDL2"] = True  # only used for samples
        tc.cache_variables["FILAMENT_SUPPORTS_EGL_ON_LINUX"] = self.options.get_safe("with_egl", False)
        tc.cache_variables["FILAMENT_SUPPORTS_METAL"] = self.options.get_safe("with_metal", False)
        tc.cache_variables["FILAMENT_SUPPORTS_OPENGL"] = self.options.get_safe("with_opengl", False)
        tc.cache_variables["FILAMENT_SUPPORTS_OSMESA"] = False
        tc.cache_variables["FILAMENT_SUPPORTS_VULKAN"] = self.options.with_vulkan
        tc.cache_variables["FILAMENT_SUPPORTS_WAYLAND"] = self.options.get_safe("with_wayland", False)
        tc.cache_variables["FILAMENT_SUPPORTS_WEBGPU"] = self.options.with_webgpu
        tc.cache_variables["FILAMENT_SUPPORTS_XCB"] = self.options.get_safe("with_xcb", False)
        tc.cache_variables["FILAMENT_SUPPORTS_XLIB"] = self.options.get_safe("with_xlib", False)
        tc.cache_variables["FILAMENT_USE_ABSEIL_LOGGING"] = self.options.use_abseil_logging
        tc.cache_variables["WEBGL_PTHREADS"] = self.options.get_safe("enable_wasm_threads", False)
        tc.cache_variables["USE_STATIC_LIBCXX"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        # Give the libraries saner names... `utils` and `math` in a global namespace are not ok.
        tc.cache_variables["CMAKE_STATIC_LIBRARY_PREFIX_CXX"] = "filament_" if self.settings.os == "Windows" else "libfilament_"
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("cgltf", "cmake_target_name", "cgltf")
        deps.set_property("draco", "cmake_target_name", "dracodec")
        deps.set_property("civetweb", "cmake_target_name", "civetweb")
        deps.set_property("glslang", "cmake_target_name", "glslang")
        deps.set_property("imgui", "cmake_target_name", "imgui")
        deps.set_property("jsmn", "cmake_target_name", "jsmn")
        deps.set_property("libbasisu", "cmake_target_aliases", ["basis_encoder", "basis_transcoder"])
        deps.set_property("libpng", "cmake_target_name", "png::png")
        deps.set_property("meshoptimizer", "cmake_target_name", "meshoptimizer")
        deps.set_property("mikktspace", "cmake_target_name", "mikktspace")
        deps.set_property("musl-getopt", "cmake_target_name", "getopt")
        deps.set_property("smol-v", "cmake_target_name", "smol-v")
        deps.set_property("stb", "cmake_target_name", "stb")
        deps.set_property("tinyexr", "cmake_target_name", "tinyexr")
        deps.set_property("zlib-ng", "cmake_target_name", "z")
        deps.set_property("zstd", "cmake_target_name", "zstd")
        deps.set_property("spirv-headers", "cmake_target_name", "SPIRV-Headers")
        deps.set_property("spirv-tools", "cmake_target_name", "spirv-tools")
        deps.set_property("spirv-cross", "cmake_target_name", "spirv-cross")
        deps.set_property("spirv-tools::spirv-tools-core", "cmake_target_name", "SPIRV-Tools")
        deps.set_property("spirv-tools::spirv-tools-opt", "cmake_target_name", "SPIRV-Tools-opt")
        deps.set_property("spirv-cross::spirv-cross-core", "cmake_target_name", "spirv-cross-core")
        deps.set_property("spirv-cross::spirv-cross-glsl", "cmake_target_name", "spirv-cross-glsl")
        deps.set_property("vulkan-memory-allocator", "cmake_target_name", "vkmemalloc")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "docs"))
        rm(self, "LICENSE", self.package_folder)
        rm(self, "README.md", self.package_folder)

    def package_info(self):
        # The project does not export any CMake config or .pc files

        # filament: Main filament library
        self.cpp_info.components["filament_"].set_property("cmake_target_name", "filament::filament")
        self.cpp_info.components["filament_"].libs = ["filament_filament"]
        self.cpp_info.components["filament_"].requires = [
            "backend",
            "utils",
            "filaflat",
            "filabridge",
            "zstd::zstd",
        ]
        if self.options.use_abseil_logging:
            self.cpp_info.components["filament_"].requires.append("abseil::log")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["filament_"].system_libs = ["dl"]

        # utils: Utility library (threads, memory, data structures, etc.)
        utils = self.cpp_info.components["utils"]
        utils.set_property("cmake_target_name", "filament::utils")
        utils.libs = ["filament_utils"]
        if self.options.get_safe("enable_wasm_threads"):
            utils.defines.append("FILAMENT_WASM_THREADS")
            utils.system_libs.append("pthread")
        utils.requires = ["tsl-robin-map::tsl-robin-map"]
        if self.settings.os == "Android":
            utils.system_libs += ["log", "dl", "android"]
            if self.options.with_perfetto:
                utils.requires.append("perfetto::perfetto")
        elif self.settings.os == "Windows":
            utils.system_libs.append("Shlwapi")
        elif is_apple_os(self):
            utils.frameworks.append("Foundation")
        elif self.settings.os in ["Linux", "FreeBSD"]:
            utils.system_libs += ["m", "dl", "pthread"]

        # backend: Backend library
        backend = self.cpp_info.components["backend"]
        backend.set_property("cmake_target_name", "filament::backend")
        backend.libs = ["filament_backend"]
        backend.requires = ["utils", "abseil::str_format"]
        if self.options.use_abseil_logging:
            backend.defines.append("FILAMENT_USE_ABSEIL_LOGGING")
            backend.requires += ["abseil::log"]
        if self.settings.os == "Android":
            if self.options.with_opengl:
                backend.system_libs += ["GLESv3", "EGL"]
            backend.system_libs += ["android"]
        if is_apple_os(self) and not self.settings.os != "iOS":
            backend.frameworks += ["Cocoa", "QuartzCore"]
        if self.options.with_vulkan:
            backend.requires += ["bluevk", "vkshaders", "smol-v::smol-v"]
        if self.options.get_safe("with_opengl"):
            backend.requires += ["bluegl"]
        if self.options.with_webgpu:
            backend.requires += ["dawn::dawn"]
        if self.options.get_safe("with_metal"):
            backend.frameworks += ["Metal", "CoreVideo"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            backend.system_libs += ["dl"]
            if self.options.with_egl:
                backend.requires += ["egl::egl"]

        # bluevk: Vulkan bindings for macOS, Linux, Windows and Android
        if self.options.with_vulkan:
            self.cpp_info.components["bluevk"].set_property("cmake_target_name", "filament::bluevk")
            self.cpp_info.components["bluevk"].libs = ["filament_bluevk"]
            self.cpp_info.components["bluevk"].requires = [
                "utils",
                "vulkan-memory-allocator::vulkan-memory-allocator", "spirv-headers::spirv-headers",
            ]

        # bluegl: OpenGL bindings for macOS, Linux and Windows
        if self.options.get_safe("with_opengl"):
            self.cpp_info.components["bluegl"].set_property("cmake_target_name", "filament::bluegl")
            self.cpp_info.components["bluegl"].libs = ["filament_bluegl"]
            if self.settings.os == "Windows":
                self.cpp_info.components["bluegl"].system_libs += ["gdi32"]
            self.cpp_info.components["bluegl"].requires = ["opengl::opengl"]

        # filabridge: Library shared by the Filament engine and host tools
        self.cpp_info.components["filabridge"].set_property("cmake_target_name", "filament::filabridge")
        self.cpp_info.components["filabridge"].libs = ["filament_filabridge"]
        self.cpp_info.components["filabridge"].requires = ["utils"]

        # filaflat: Serialization/deserialization library used for materials
        self.cpp_info.components["filaflat"].set_property("cmake_target_name", "filament::filaflat")
        self.cpp_info.components["filaflat"].libs = ["filament_filaflat"]
        self.cpp_info.components["filaflat"].requires = ["utils", "filabridge", "smol-v::smol-v"]

        # filamat: Material generation library
        self.cpp_info.components["filamat"].set_property("cmake_target_name", "filament::filamat")
        self.cpp_info.components["filamat"].libs = ["filament_filamat"]
        self.cpp_info.components["filamat"].requires = [
            "utils",
            "shaders",
            "filabridge",
            "smol-v::smol-v",
            "glslang::glslang",
            "spirv-tools::spirv-tools",
            "spirv-cross::spirv-cross",
        ]
        if self.options.with_webgpu:
            self.cpp_info.components["filamat"].requires += ["dawn::dawn"]

        # geometry: Mesh-related utilities
        self.cpp_info.components["geometry"].set_property("cmake_target_name", "filament::geometry")
        self.cpp_info.components["geometry"].libs = ["filament_geometry"]
        self.cpp_info.components["geometry"].requires = ["utils", "meshoptimizer::meshoptimizer", "mikktspace::mikktspace"]

        # image: Image filtering and simple transforms
        self.cpp_info.components["image"].set_property("cmake_target_name", "filament::image")
        self.cpp_info.components["image"].libs = ["filament_image"]
        self.cpp_info.components["image"].requires = ["utils"]

        # ibl: IBL generation tools
        self.cpp_info.components["ibl"].set_property("cmake_target_name", "filament::ibl")
        self.cpp_info.components["ibl"].libs = ["filament_ibl"]
        self.cpp_info.components["ibl"].requires = ["utils"]

        self.cpp_info.components["ibl-lite"].set_property("cmake_target_name", "filament::ibl-lite")
        self.cpp_info.components["ibl-lite"].libs = ["filament_ibl-lite"]
        self.cpp_info.components["ibl-lite"].defines.append("FILAMENT_IBL_LITE")
        self.cpp_info.components["ibl-lite"].requires = ["utils"]

        self.cpp_info.components["iblprefilter"].set_property("cmake_target_name", "filament::iblprefilter")
        self.cpp_info.components["iblprefilter"].libs = ["filament_filament-iblprefilter"]
        self.cpp_info.components["iblprefilter"].requires = ["utils", "filament_"]

        self.cpp_info.components["generatePrefilterMipmap"].set_property("cmake_target_name", "filament::generatePrefilterMipmap")
        self.cpp_info.components["generatePrefilterMipmap"].libs = ["filament_filament-generatePrefilterMipmap"]
        self.cpp_info.components["generatePrefilterMipmap"].requires = ["utils", "ibl", "filament_"]

        # camutils: Camera manipulation utilities
        self.cpp_info.components["camutils"].set_property("cmake_target_name", "filament::camutils")
        self.cpp_info.components["camutils"].libs = ["filament_camutils"]

        # gltfio: Loader for glTF 2.0
        self.cpp_info.components["gltfio_core"].set_property("cmake_target_name", "filament::gltfio_core")
        self.cpp_info.components["gltfio_core"].libs = ["filament_gltfio_core"]
        self.cpp_info.components["gltfio_core"].defines.append("GLTFIO_DRACO_SUPPORTED")
        self.cpp_info.components["gltfio_core"].requires = [
            "utils", "filament_", "uberarchive", "uberzlib", "ktxreader", "geometry",
            "cgltf::cgltf", "stb::stb", "draco::draco", "meshoptimizer::meshoptimizer",
        ]
        self.cpp_info.components["uberarchive"].libs = ["uberarchive"]
        if self.settings.os not in ["Android", "iOS", "Emscripten"]:
            self.cpp_info.components["gltfio"].set_property("cmake_target_name", "filament::gltfio")
            self.cpp_info.components["gltfio"].libs = ["filament_gltfio"]
            self.cpp_info.components["gltfio"].requires = ["gltfio_core", "filamat"]


        # filameshio: Tiny filamesh parsing library (see also tools/filamesh)
        self.cpp_info.components["filameshio"].set_property("cmake_target_name", "filament::filameshio")
        self.cpp_info.components["filameshio"].libs = ["filament_filameshio"]
        self.cpp_info.components["filameshio"].requires = ["filament_", "meshoptimizer::meshoptimizer"]

        # fgviewer: frame graph viewer
        if self.options.build_fgviewer:
            self.cpp_info.components["fgviewer"].set_property("cmake_target_name", "filament::fgviewer")
            self.cpp_info.components["fgviewer"].libs = ["fgviewer"]
            self.cpp_info.components["fgviewer"].requires = ["utils", "civetweb::civetweb"]
            self.cpp_info.components["filament_"].requires.append("fgviewer")

        # viewer: glTF viewer library (requires gltfio)
        if not self._is_mobile_target:
            self.cpp_info.components["viewer"].set_property("cmake_target_name", "filament::viewer")
            self.cpp_info.components["viewer"].libs = ["filament_viewer"]
            self.cpp_info.components["viewer"].requires = [
                "filament_", "gltfio_core", "filagui", "camutils", "jsmn::jsmn", "civetweb::civetweb",
            ]

        # ktxreader: KTX reader
        self.cpp_info.components["ktxreader"].set_property("cmake_target_name", "filament::ktxreader")
        self.cpp_info.components["ktxreader"].libs = ["filament_ktxreader"]
        self.cpp_info.components["ktxreader"].requires = ["utils", "image", "filament_", "libbasisu::libbasisu"]

        # matp: Material parser
        self.cpp_info.components["matp"].set_property("cmake_target_name", "filament::matp")
        self.cpp_info.components["matp"].libs = ["filament_matp"]
        self.cpp_info.components["matp"].requires = ["musl-getopt::musl-getopt", "filamat", "filabridge", "utils"]

        # matdbg: Material debugger
        if self.options.build_matdbg:
            self.cpp_info.components["matdbg"].set_property("cmake_target_name", "filament::matdbg")
            self.cpp_info.components["matdbg"].libs = ["matdbg"]
            self.cpp_info.components["matdbg"].requires = ["utils", "filaflat", "filamat", "civetweb::civetweb", "filabridge"]
            self.cpp_info.components["filament_"].requires.append("matdbg")

        self.cpp_info.components["filagui"].set_property("cmake_target_name", "filament::filagui")
        self.cpp_info.components["filagui"].libs = ["filament_filagui"]
        self.cpp_info.components["filagui"].requires = ["imgui::imgui", "filament_"]

        self.cpp_info.components["uberzlib"].set_property("cmake_target_name", "filament::uberzlib")
        self.cpp_info.components["uberzlib"].libs = ["filament_uberzlib"]
        self.cpp_info.components["uberzlib"].requires = ["utils", "filabridge", "zstd::zstd"]

        self.cpp_info.components["shaders"].set_property("cmake_target_name", "filament::shaders")
        self.cpp_info.components["shaders"].libs = ["shaders"]

        self.cpp_info.components["vkshaders"].set_property("cmake_target_name", "filament::vkshaders")
        self.cpp_info.components["vkshaders"].libs = ["vkshaders"]

        # Used only internally for tools, not installed
        self.cpp_info.components["mathio"].requires = []
        self.cpp_info.components["imageio"].requires = ["image", "libpng::libpng", "tinyexr::tinyexr", "zlib-ng::zlib-ng", "libbasisu::libbasisu"]

        # Tools
        self.cpp_info.components["_tools"].requires = ["mathio", "imageio", "assimp::assimp"]
