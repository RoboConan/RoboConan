import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir, save

required_conan_version = ">=2.21"  # CMakeDeps cmake_extra_variables


class MagnumPluginsConan(ConanFile):
    name = "magnum-plugins"
    description = "Plugins for the Magnum C++11/C++14 graphics engine"
    license = "MIT"
    homepage = "https://magnum.graphics"
    topics = ("magnum", "graphics", "rendering", "3d", "2d", "opengl")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "shared_plugins": [True, False],
        # Audio importers
        "drflac_audioimporter": [True, False],
        "drmp3_audioimporter": [True, False],
        "drwav_audioimporter": [True, False],
        "faad2_audioimporter": [True, False],
        "stbvorbis_audioimporter": [True, False],
        # Fonts
        "freetype_font": [True, False],
        "harfbuzz_font": [True, False],
        "stbtruetype_font": [True, False],
        # Image converters
        "basis_imageconverter": [True, False],
        "bcdec_imageconverter": [True, False],
        "etcdec_imageconverter": [True, False],
        "jpeg_imageconverter": [True, False],
        "ktx_imageconverter": [True, False],
        "miniexr_imageconverter": [True, False],
        "openexr_imageconverter": [True, False],
        "png_imageconverter": [True, False],
        "stbdxt_imageconverter": [True, False],
        "stb_imageconverter": [True, False],
        "stbresize_imageconverter": [True, False],
        "webp_imageconverter": [True, False],
        # Importers
        "assimp_importer": [True, False],
        "astc_importer": [True, False],
        "avif_importer": [True, False],
        "basis_importer": [True, False],
        "cgltf_importer": [True, False],
        "dds_importer": [True, False],
        "devil_imageimporter": [True, False],
        "gltf_importer": [True, False],
        "ico_importer": [True, False],
        "jpeg_importer": [True, False],
        "ktx_importer": [True, False],
        "lunasvg_importer": [True, False],
        "openexr_importer": [True, False],
        "opengex_importer": [True, False],
        "plutosvg_importer": [True, False],
        "png_importer": [True, False],
        "primitive_importer": [True, False],
        "resvg_importer": [True, False],
        "spng_importer": [True, False],
        "stanford_importer": [True, False],
        "stb_imageimporter": [True, False],
        "stl_importer": [True, False],
        "tinygltf_importer": [True, False],
        "ufbx_importer": [True, False],
        "webp_importer": [True, False],
        # Scene converters
        "gltf_sceneconverter": [True, False],
        "meshoptimizer_sceneconverter": [True, False],
        "stanford_sceneconverter": [True, False],
        # Shader converters
        "glslang_shaderconverter": [True, False],
        "spirvtools_shaderconverter": [True, False],
        # Deprecated library used by OpenGexImporter
        "openddl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "shared_plugins": True,
        # Audio importers
        "drflac_audioimporter": True,
        "drmp3_audioimporter": True,
        "drwav_audioimporter": True,
        "faad2_audioimporter": False,
        "stbvorbis_audioimporter": True,
        # Fonts
        "freetype_font": True,
        "harfbuzz_font": True,
        "stbtruetype_font": True,
        # Image converters
        "basis_imageconverter": False,
        "bcdec_imageconverter": True,
        "etcdec_imageconverter": True,
        "jpeg_imageconverter": True,
        "ktx_imageconverter": True,
        "miniexr_imageconverter": True,
        "openexr_imageconverter": True,
        "png_imageconverter": True,
        "stbdxt_imageconverter": True,
        "stb_imageconverter": True,
        "stbresize_imageconverter": True,
        "webp_imageconverter": True,
        # Importers
        "assimp_importer": True,
        "astc_importer": True,
        "avif_importer": True,
        "basis_importer": False,
        "cgltf_importer": False,
        "dds_importer": True,
        "devil_imageimporter": True,
        "gltf_importer": True,
        "ico_importer": True,
        "jpeg_importer": True,
        "ktx_importer": True,
        "lunasvg_importer": True,
        "openexr_importer": True,
        "opengex_importer": True,
        "plutosvg_importer": True,
        "png_importer": True,
        "primitive_importer": True,
        "resvg_importer": False,
        "spng_importer": True,
        "stanford_importer": True,
        "stb_imageimporter": True,
        "stl_importer": True,
        "tinygltf_importer": True,
        "ufbx_importer": True,
        "webp_importer": True,
        # Scene converters
        "gltf_sceneconverter": True,
        "meshoptimizer_sceneconverter": True,
        "stanford_sceneconverter": True,
        # Shader converters
        "glslang_shaderconverter": True,
        "spirvtools_shaderconverter": True,
        # Deprecated library used by OpenGexImporter
        "openddl": True,
    }
    implements = ["auto_shared_fpic"]

    def layout(self):
        cmake_layout(self, src_folder="src")

    def config_options(self):
        if self.settings.os == "Emscripten":
            self.options.shared_plugins = False

    def configure(self):
        if self.options.harfbuzz_font:
            self.options.freetype_font.value = True
        if self.options.cgltf_importer:
            self.options.gltf_importer.value = True
        if self.options.opengex_importer:
            self.options.openddl.value = True

    def requirements(self):
        # https://github.com/mosra/magnum-plugins/blob/6430818ad2790d1acb7f74b727ac4f1c25295228/src/MagnumPlugins/StlImporter/StlImporter.h#L34-L36
        self.requires("magnum/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.assimp_importer:
            self.requires("assimp/[^5.1.6]")
        if self.options.avif_importer:
            self.requires("libavif/[^1.3.0]")
        if self.options.devil_imageimporter:
            self.requires("devil/[^1.8.0]")
        if self.options.freetype_font or self.options.harfbuzz_font:
            self.requires("freetype/[^2.13.3]")
        if self.options.glslang_shaderconverter:
            self.requires("glslang/[^1.4.321.0]")
        if self.options.harfbuzz_font:
            self.requires("harfbuzz/[^11.4.1]")
        if self.options.jpeg_importer or self.options.jpeg_imageconverter:
            self.requires("libjpeg-meta/latest")
        if self.options.lunasvg_importer:
            self.requires("lunasvg/[^3.5.0]")
        if self.options.meshoptimizer_sceneconverter:
            self.requires("meshoptimizer/[<2]")
        if self.options.openexr_importer or self.options.openexr_imageconverter:
            self.requires("openexr/[^3.4.9]")
        if self.options.plutosvg_importer:
            self.requires("plutosvg/[^0.0.7]")
        if self.options.png_importer or self.options.png_imageconverter:
            self.requires("libpng/[~1.6]")
        if self.options.spirvtools_shaderconverter:
            self.requires("spirv-tools/[^1.4.321.0]")
        if self.options.spng_importer:
            self.requires("libspng/[^0.7.4]")
        if self.options.webp_importer or self.options.webp_imageconverter:
            self.requires("libwebp/[^1.6.0]")

    def build_requirements(self):
        self.tool_requires("corrade/<host_version>")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)
        if self.options.shared != self.dependencies["magnum"].options.shared:
            raise ConanInvalidConfiguration(
                "The 'shared' option must match magnum:shared because upstream inherits "
                "MAGNUM_BUILD_STATIC from the Magnum package"
            )
        if self.options.basis_imageconverter or self.options.basis_importer:
            raise ConanInvalidConfiguration("BasisUniversal does not have a RoboConan recipe")
        if self.options.faad2_audioimporter:
            raise ConanInvalidConfiguration("FAAD2 does not have a RoboConan recipe")
        if self.options.resvg_importer:
            raise ConanInvalidConfiguration("resvg does not have a RoboConan recipe")

        magnum = self.dependencies["magnum"].options
        required_components = {
            "audio": any(self.options.get_safe(option, False) for option in (
                "drflac_audioimporter", "drmp3_audioimporter", "drwav_audioimporter",
                "faad2_audioimporter", "stbvorbis_audioimporter",
            )),
            "mesh_tools": any(self.options.get_safe(option, False) for option in (
                "meshoptimizer_sceneconverter", "stanford_importer", "stanford_sceneconverter",
                "stl_importer", "ufbx_importer",
            )),
            "primitives": self.options.primitive_importer,
            "shader_tools": self.options.glslang_shaderconverter or self.options.spirvtools_shaderconverter,
            "text": self.options.freetype_font or self.options.harfbuzz_font or self.options.stbtruetype_font,
            "trade": any(plugin[0] not in {
                "drflac_audioimporter", "drmp3_audioimporter", "drwav_audioimporter",
                "faad2_audioimporter", "stbvorbis_audioimporter", "freetype_font",
                "harfbuzz_font", "stbtruetype_font", "glslang_shaderconverter",
                "spirvtools_shaderconverter",
            } for plugin in self._plugins),
        }
        for option, required in required_components.items():
            if required and not magnum.get_safe(option, False):
                raise ConanInvalidConfiguration(f"Enabled plugins require 'magnum:{option}=True'")
        if any(self.options.get_safe(option, False) for option in (
            "assimp_importer", "gltf_importer", "opengex_importer", "tinygltf_importer", "ufbx_importer",
        )) and not magnum.any_image_importer:
            raise ConanInvalidConfiguration("Enabled scene importers require 'magnum:any_image_importer=True'")
        if any(self.options.get_safe(option, False) for option in (
            "cgltf_importer", "openddl", "opengex_importer", "tinygltf_importer",
        )) and not magnum.build_deprecated:
            raise ConanInvalidConfiguration("CgltfImporter, OpenGexImporter and TinyGltfImporter require 'magnum:build_deprecated=True'")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["MAGNUM_BUILD_STATIC"] = not self.options.shared
        tc.cache_variables["MAGNUM_BUILD_STATIC_PIC"] = self.options.get_safe("fPIC", False)
        tc.cache_variables["MAGNUM_BUILD_PLUGINS_STATIC"] = not self.options.shared_plugins
        tc.cache_variables["MAGNUM_BUILD_TESTS"] = False
        tc.cache_variables["MAGNUM_BUILD_GL_TESTS"] = False
        if self.options.assimp_importer or self.options.glslang_shaderconverter or self.options.spirvtools_shaderconverter:
            # https://github.com/mosra/magnum-plugins/blob/6430818ad2790d1acb7f74b727ac4f1c25295228/src/MagnumPlugins/SpirvToolsShaderConverter/CMakeLists.txt#L71-L82
            # Ensure configuration-specific CMakeDeps usage requirements are
            # available to upstream dependency try_compile() checks.
            tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        # These normally come from upstream's FindMagnum.cmake. CMakeDeps
        # finds Magnum's generated config first, which intentionally contains
        # target metadata only.
        tc.cache_variables["CMAKE_INSTALL_DATADIR"] = "share"
        tc.cache_variables["MAGNUM_INCLUDE_INSTALL_DIR"] = "include/Magnum"
        if self.options.openddl:
            tc.cache_variables["MAGNUM_BINARY_INSTALL_DIR"] = "bin"
            tc.cache_variables["MAGNUM_LIBRARY_INSTALL_DIR"] = "lib"
        if self.options.tinygltf_importer:
            tc.cache_variables["MAGNUM_EXTERNAL_INCLUDE_INSTALL_DIR"] = "include/MagnumExternal"
        if self._plugins:
            tc.cache_variables["MAGNUM_PLUGINS_INCLUDE_INSTALL_DIR"] = "include/MagnumPlugins"
        categories = {
            "audioimporters": "AUDIOIMPORTER",
            "fonts": "FONT",
            "fontconverters": "FONTCONVERTER",
            "imageconverters": "IMAGECONVERTER",
            "importers": "IMPORTER",
            "sceneconverters": "SCENECONVERTER",
            "shaderconverters": "SHADERCONVERTER",
        }
        for directory in {plugin[3] for plugin in self._plugins}:
            category = categories[directory]
            for build_type, suffix in (("DEBUG", "-d"), ("RELEASE", "")):
                tc.cache_variables[
                    f"MAGNUM_PLUGINS_{category}_{build_type}_BINARY_INSTALL_DIR"
                ] = f"bin/magnum{suffix}/{directory}"
                tc.cache_variables[
                    f"MAGNUM_PLUGINS_{category}_{build_type}_LIBRARY_INSTALL_DIR"
                ] = f"lib/magnum{suffix}/{directory}"
        for option, _ in self.options.items():
            if option not in {"shared", "fPIC", "shared_plugins", "openddl"}:
                tc.cache_variables[f"MAGNUM_WITH_{option.upper().replace('_', '')}"] = self.options.get_safe(option)
        tc.cache_variables["MAGNUM_WITH_OPENDDL"] = self.options.openddl
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.assimp_importer:
            deps.set_property("assimp", "cmake_file_name", "Assimp")
            deps.set_property("assimp", "cmake_target_name", "Assimp::Assimp")
        if self.options.devil_imageimporter:
            deps.set_property("devil", "cmake_file_name", "DevIL")
            deps.set_property("devil", "cmake_extra_variables", {
                "IL_INCLUDE_DIR": os.path.join(
                    self.dependencies["devil"].package_folder, "include"
                ).replace("\\", "/"),
                "IL_LIBRARIES": "DevIL::IL",
                "ILU_LIBRARIES": "DevIL::ILU",
            })
        if self.options.freetype_font or self.options.harfbuzz_font:
            deps.set_property("freetype", "cmake_file_name", "Freetype")
        if self.options.glslang_shaderconverter:
            # https://github.com/mosra/magnum-plugins/blob/6430818ad2790d1acb7f74b727ac4f1c25295228/modules/FindGlslang.cmake#L153-L160
            # The upstream compatibility target exposes both include roots and
            # links SPIRV, which is the top-level library on glslang 14.
            self.dependencies["glslang"].cpp_info.components["spirv"].includedirs.append(
                os.path.join(self.dependencies["glslang"].package_folder, "include", "glslang")
            )
            deps.set_property("glslang", "cmake_file_name", "Glslang")
            deps.set_property("glslang::spirv", "cmake_target_name", "Glslang::Glslang")
        if self.options.harfbuzz_font:
            deps.set_property("harfbuzz", "cmake_file_name", "HarfBuzz")
            deps.set_property("harfbuzz::harfbuzz_", "cmake_target_name", "HarfBuzz::HarfBuzz")
        if self.options.lunasvg_importer:
            # Match the include directory exported by lunasvg's installed
            # lunasvg::lunasvg target.
            # https://github.com/sammycage/lunasvg/blob/v3.5.0/CMakeLists.txt#L45-L48
            self.dependencies["lunasvg"].cpp_info.includedirs.append(os.path.join(
                self.dependencies["lunasvg"].package_folder, "include", "lunasvg"
            ))
        if self.options.openexr_importer or self.options.openexr_imageconverter:
            deps.set_property("openexr", "cmake_find_mode", "module")
        if self.options.plutosvg_importer:
            deps.set_property("plutosvg", "cmake_file_name", "plutosvg")
            deps.set_property("plutosvg", "cmake_target_name", "plutosvg::plutosvg")
        if self.options.spirvtools_shaderconverter:
            deps.set_property("spirv-tools", "cmake_file_name", "SpirvTools")
            deps.set_property("spirv-tools::spirv-tools-core", "cmake_target_name", "SpirvTools::SpirvTools")
            deps.set_property("spirv-tools::spirv-tools-opt", "cmake_target_name", "SpirvTools::Opt")
        if self.options.spng_importer:
            deps.set_property("libspng", "cmake_file_name", "Spng")
            deps.set_property("libspng", "cmake_target_name", "Spng::Spng")
        if self.options.webp_importer or self.options.webp_imageconverter:
            deps.set_property("libwebp", "cmake_file_name", "WebP")
            deps.set_property("libwebp::webp", "cmake_target_name", "WebP::WebP")
        deps.generate()

    def _patch_sources(self):
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        'set(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/modules/" ${CMAKE_MODULE_PATH})',
                        'list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/modules/")')
        if self.options.plutosvg_importer:
            # The packaged PlutoSVG 0.0.7 C API uses public _t suffixes while
            # this snapshot tracks the names on PlutoSVG main.
            # https://github.com/sammycage/plutosvg/blob/v0.0.7/source/plutosvg.h#L73
            # https://github.com/sammycage/plutovg/blob/v1.3.1/include/plutovg.h#L276
            source = os.path.join(
                self.source_folder, "src", "MagnumPlugins", "PlutoSvgImporter", "PlutoSvgImporter.cpp"
            )
            replace_in_file(self, source, "plutosvg_document*", "plutosvg_document_t*")
            replace_in_file(self, source, "plutovg_matrix matrix", "plutovg_matrix_t matrix")
            # A deleted copy constructor makes State a non-aggregate in C++20,
            # so the brace construction in Corrade::Pointer needs an explicit
            # two-argument constructor.
            replace_in_file(
                self,
                source,
                "struct PlutoSvgImporter::State {\n    ~State() {",
                "struct PlutoSvgImporter::State {\n"
                "    explicit State(Containers::Array<char>&& data, plutosvg_document_t* document): "
                "data{Utility::move(data)}, document{document} {}\n\n"
                "    ~State() {",
            )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))

        if not self.options.shared_plugins:
            targets = "\n".join(textwrap.dedent(f"""\
                if(TARGET MagnumPlugins::{target})
                    set_property(TARGET MagnumPlugins::{target} APPEND PROPERTY INTERFACE_SOURCES
                        "${{CMAKE_CURRENT_LIST_DIR}}/../../../include/MagnumPlugins/{library}/importStaticPlugin.cpp")
                endif()
            """) for _, target, library, _, _ in self._plugins)
            save(self, os.path.join(
                self.package_folder, "share", "conan", "magnum-plugins", "conan-magnum-plugins-targets.cmake"
            ), targets)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "MagnumPlugins")
        if not self.options.shared_plugins:
            self.cpp_info.set_property("cmake_build_modules", [
                "share/conan/magnum-plugins/conan-magnum-plugins-targets.cmake",
            ])

        suffix = "-d" if self.settings.build_type == "Debug" else ""
        plugin_suffix = suffix if not self.options.shared_plugins else ""
        plugin_libdir = "magnum-d" if self.settings.build_type == "Debug" and self.options.shared_plugins else "magnum"

        if self.options.openddl:
            openddl = self.cpp_info.components["openddl"]
            openddl.set_property("cmake_target_name", "MagnumPlugins::OpenDdl")
            openddl.libs = [f"MagnumOpenDdl{suffix}"]
            openddl.requires = ["magnum::magnum_main"]

        for component, target, library, folder, requires in self._plugins:
            plugin = self.cpp_info.components[component]
            plugin.set_property("cmake_target_name", f"MagnumPlugins::{target}")
            if not self.options.shared_plugins:
                plugin.libs = [f"{library}{plugin_suffix}"]
            plugin.libdirs = [f"lib/{plugin_libdir}/{folder}"]
            plugin.requires = requires

        plugin_dir = "bin" if self.settings.os == "Windows" else "lib"
        self.conf_info.define_path("user.magnum-plugins:plugins_basepath", os.path.join(
            self.package_folder, plugin_dir, plugin_libdir,
        ))

    @property
    def _plugins(self):
        return _plugins(self.options, self.settings, self.options.shared_plugins)


def _plugins(opts, settings, shared_plugins):
    trade = ["magnum::trade"]
    audio = ["magnum::audio"]
    text = ["magnum::text"]
    any_image = ["magnum::any_image_importer"] if settings.os == "Windows" or not shared_plugins else []
    plugins = (
        ("drflac_audioimporter", "DrFlacAudioImporter", "DrFlacAudioImporter", "audioimporters", audio),
        ("drmp3_audioimporter", "DrMp3AudioImporter", "DrMp3AudioImporter", "audioimporters", audio),
        ("drwav_audioimporter", "DrWavAudioImporter", "DrWavAudioImporter", "audioimporters", audio),
        ("faad2_audioimporter", "Faad2AudioImporter", "Faad2AudioImporter", "audioimporters", audio),
        ("stbvorbis_audioimporter", "StbVorbisAudioImporter", "StbVorbisAudioImporter", "audioimporters", audio),
        ("freetype_font", "FreeTypeFont", "FreeTypeFont", "fonts", text + ["freetype::freetype"]),
        ("harfbuzz_font", "HarfBuzzFont", "HarfBuzzFont", "fonts", text + ["freetype_font", "harfbuzz::harfbuzz_"]),
        ("stbtruetype_font", "StbTrueTypeFont", "StbTrueTypeFont", "fonts", text),
        ("basis_imageconverter", "BasisImageConverter", "BasisImageConverter", "imageconverters", trade),
        ("bcdec_imageconverter", "BcDecImageConverter", "BcDecImageConverter", "imageconverters", trade),
        ("etcdec_imageconverter", "EtcDecImageConverter", "EtcDecImageConverter", "imageconverters", trade),
        ("jpeg_imageconverter", "JpegImageConverter", "JpegImageConverter", "imageconverters", trade + ["libjpeg-meta::jpeg"]),
        ("ktx_imageconverter", "KtxImageConverter", "KtxImageConverter", "imageconverters", trade),
        ("miniexr_imageconverter", "MiniExrImageConverter", "MiniExrImageConverter", "imageconverters", trade),
        ("openexr_imageconverter", "OpenExrImageConverter", "OpenExrImageConverter", "imageconverters", trade + ["openexr::openexr_openexr"]),
        ("png_imageconverter", "PngImageConverter", "PngImageConverter", "imageconverters", trade + ["libpng::libpng"]),
        ("stbdxt_imageconverter", "StbDxtImageConverter", "StbDxtImageConverter", "imageconverters", trade),
        ("stb_imageconverter", "StbImageConverter", "StbImageConverter", "imageconverters", trade),
        ("stbresize_imageconverter", "StbResizeImageConverter", "StbResizeImageConverter", "imageconverters", trade),
        ("webp_imageconverter", "WebPImageConverter", "WebPImageConverter", "imageconverters", trade + ["libwebp::webp"]),
        ("assimp_importer", "AssimpImporter", "AssimpImporter", "importers", trade + any_image + ["assimp::assimp"]),
        ("astc_importer", "AstcImporter", "AstcImporter", "importers", trade),
        ("avif_importer", "AvifImporter", "AvifImporter", "importers", trade + ["libavif::libavif"]),
        ("basis_importer", "BasisImporter", "BasisImporter", "importers", trade),
        ("cgltf_importer", "CgltfImporter", "CgltfImporter", "importers", ["gltf_importer"]),
        ("dds_importer", "DdsImporter", "DdsImporter", "importers", trade),
        ("devil_imageimporter", "DevIlImageImporter", "DevIlImageImporter", "importers", trade + ["devil::IL", "devil::ILU"]),
        ("gltf_importer", "GltfImporter", "GltfImporter", "importers", trade + any_image),
        ("ico_importer", "IcoImporter", "IcoImporter", "importers", trade),
        ("jpeg_importer", "JpegImporter", "JpegImporter", "importers", trade + ["libjpeg-meta::jpeg"]),
        ("ktx_importer", "KtxImporter", "KtxImporter", "importers", trade),
        ("lunasvg_importer", "LunaSvgImporter", "LunaSvgImporter", "importers", trade + ["lunasvg::lunasvg"]),
        ("openexr_importer", "OpenExrImporter", "OpenExrImporter", "importers", trade + ["openexr::openexr_openexr"]),
        ("opengex_importer", "OpenGexImporter", "OpenGexImporter", "importers", trade + any_image + ["openddl"]),
        ("plutosvg_importer", "PlutoSvgImporter", "PlutoSvgImporter", "importers", trade + ["plutosvg::plutosvg"]),
        ("png_importer", "PngImporter", "PngImporter", "importers", trade + ["libpng::libpng"]),
        ("primitive_importer", "PrimitiveImporter", "PrimitiveImporter", "importers", trade + ["magnum::primitives"]),
        ("resvg_importer", "ResvgImporter", "ResvgImporter", "importers", trade),
        ("spng_importer", "SpngImporter", "SpngImporter", "importers", trade + ["libspng::libspng"]),
        ("stanford_importer", "StanfordImporter", "StanfordImporter", "importers", trade + ["magnum::mesh_tools"]),
        ("stb_imageimporter", "StbImageImporter", "StbImageImporter", "importers", trade),
        ("stl_importer", "StlImporter", "StlImporter", "importers", trade + ["magnum::mesh_tools"]),
        ("tinygltf_importer", "TinyGltfImporter", "TinyGltfImporter", "importers", trade + any_image),
        ("ufbx_importer", "UfbxImporter", "UfbxImporter", "importers", trade + any_image + ["magnum::mesh_tools"]),
        ("webp_importer", "WebPImporter", "WebPImporter", "importers", trade + ["libwebp::webp"]),
        ("gltf_sceneconverter", "GltfSceneConverter", "GltfSceneConverter", "sceneconverters", trade),
        ("meshoptimizer_sceneconverter", "MeshOptimizerSceneConverter", "MeshOptimizerSceneConverter", "sceneconverters", trade + ["magnum::mesh_tools", "meshoptimizer::meshoptimizer"]),
        ("stanford_sceneconverter", "StanfordSceneConverter", "StanfordSceneConverter", "sceneconverters", trade + ["magnum::mesh_tools"]),
        ("glslang_shaderconverter", "GlslangShaderConverter", "GlslangShaderConverter", "shaderconverters", ["magnum::shader_tools", "glslang::spirv"]),
        ("spirvtools_shaderconverter", "SpirvToolsShaderConverter", "SpirvToolsShaderConverter", "shaderconverters", ["magnum::shader_tools", "spirv-tools::spirv-tools-core", "spirv-tools::spirv-tools-opt"]),
    )
    return [plugin for plugin in plugins if opts.get_safe(plugin[0], False)]
