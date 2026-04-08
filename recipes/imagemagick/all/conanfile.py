import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMakeToolchain, CMake
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps, GnuToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import MSBuild, MSBuildToolchain, is_msvc, msvc_runtime_flag, msvs_toolset, MSBuildDeps
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class ImageMagicConan(ConanFile):
    name = "imagemagick"
    description = ("ImageMagick is a free and open-source software suite for displaying, "
                   "converting, and editing raster image and vector image files")
    license = "ImageMagick"
    homepage = "https://imagemagick.org"
    topics = ("images", "manipulating")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "hdri": [True, False],
        "quantum_depth": [8, 16, 32],
        "with_zlib": [True, False],
        "with_bzlib": [True, False],
        "with_lzma": [True, False],
        "with_lcms": [True, False],
        "with_openexr": [True, False],
        "with_heic": [True, False],
        "with_jbig": [True, False],
        "with_jpeg": [True, False],
        "with_openjp2": [True, False],
        "with_pango": [True, False],
        "with_png": [True, False],
        "with_tiff": [True, False],
        "with_webp": [True, False],
        "with_xml2": [True, False],
        "with_freetype": [True, False],
        "with_djvu": [True, False],
        "utilities": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "hdri": True,
        "quantum_depth": 16,
        "with_zlib": True,
        "with_bzlib": True,
        "with_lzma": True,
        "with_lcms": True,
        "with_openexr": True,
        "with_heic": True,
        "with_jbig": True,
        "with_jpeg": True,
        "with_openjp2": True,
        "with_pango": True,
        "with_png": True,
        "with_tiff": True,
        "with_webp": False,
        "with_xml2": True,
        "with_freetype": True,
        "with_djvu": False,
        "utilities": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # None of the dependencies need transitive_headers=True
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_bzlib:
            self.requires("bzip2/[^1.0.8]")
        if self.options.with_lzma:
            self.requires("xz_utils/[^5.4.5]")
        if self.options.with_lcms:
            self.requires("lcms/[^2.16]")
        if self.options.with_openexr:
            self.requires("openexr/[^3.3.3]")
        if self.options.with_heic:
            self.requires("libheif/[^1.18.2]")
        if self.options.with_jbig:
            self.requires("jbig/20160605")
        if self.options.with_jpeg:
            self.requires("libjpeg-meta/latest")
        if self.options.with_openjp2:
            self.requires("openjpeg/[^2.5.2]")
        if self.options.with_pango:
            self.requires("pango/[^1.54.0]")
        if self.options.with_png:
            self.requires("libpng/[~1.6]")
        if self.options.with_tiff:
            self.requires("libtiff/[>=4.5 <5]")
        if self.options.with_webp:
            self.requires("libwebp/[^1.3.2]")
        if self.options.with_xml2:
            self.requires("libxml2/[^2.12.5]")
        if self.options.with_freetype:
            self.requires("freetype/[^2.13.2]")
        if self.options.with_djvu:
            self.requires("djvulibre/3.5.28")

    def validate(self):
        if is_msvc(self) and self.settings.arch not in ["x86_64", "x86", "armv8"]:
            raise ConanInvalidConfiguration(f"{self.settings.arch} architecture is not supported for MSVC")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["windows"], strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["source"], destination="ImageMagick", strip_root=True)

    @property
    def _arch_flag(self):
        return {
            "x86_64": "/x64",
            "x86": "/x86",
            "armv8": "/arm64",
        }.get(str(self.settings.arch))

    @property
    def _msvc_runtime_suffix(self):
        return {
            "MT": "StaticMT",
            "MTd": "StaticMTD",
            "MD": "DynamicMT",
            "MDd": "DynamicMT",
        }.get(msvc_runtime_flag(self))

    @property
    def _visual_studio_version(self):
        return {
            "v110": "/VS2012",
            "v120": "/VS2013",
            "v140": "/VS2015",
            "v141": "/VS2017",
            "v142": "/VS2019",
            "v143": "/VS2022",
        }.get(msvs_toolset(self), "/VS2022")

    @property
    def _msvc_runtime_flag(self):
        return {
            "MT": "/smt",
            "MTd": "/smtd",
            "MD": "/dmt",
            "MDd": "/mdt",
        }.get(msvc_runtime_flag(self))

    @property
    def _msbuild_configuration(self):
        return "Debug" if self.settings.build_type == "Debug" else "Release"

    def _generate_msvc(self):
        tc = CMakeToolchain(self)
        tc.generate()

        # https://github.com/ImageMagick/ImageMagick-Windows/blob/0b13f5dc7b4725e452f395193c0ce7f869774c21/Configure/CommandLineInfo.cpp#L128-L185
        configure_args = []
        configure_args.append(self._arch_flag)
        configure_args.append(self._msvc_runtime_flag)
        configure_args.append(self._visual_studio_version)
        configure_args.append("/hdri" if self.options.hdri else "/noHdri")
        configure_args.append(f"/Q{self.options.quantum_depth}")
        save(self, os.path.join(self.generators_folder, "configure_args"), " ".join(configure_args))

        tc = MSBuildToolchain(self)
        tc.configuration = self._msbuild_configuration
        tc.generate()

        deps = MSBuildDeps(self)
        deps.configuration = self._msbuild_configuration
        deps.generate()

    def _patch_sources_msvc(self):
        import_conan_generators = ""
        for props_file in ["conantoolchain.props", "conandeps.props"]:
            props_path = os.path.join(self.generators_folder, props_file)
            if os.path.exists(props_path):
                import_conan_generators += f'<Import Project="{props_path}" />'
        for vcxproj_file in Path(self.source_folder).rglob("*.vcxproj"):
            if props_path:
                replace_in_file(
                    self, vcxproj_file,
                    '<Import Project="$(VCTargetsPath)\\Microsoft.Cpp.targets" />',
                    f'{import_conan_generators}<Import Project="$(VCTargetsPath)\\Microsoft.Cpp.targets" />',
                )

    def _build_msvc(self):
        apply_conandata_patches(self)

        # Build and run configure.exe to generate .sln and .vcxproj files
        cmake = CMake(self)
        cmake.configure(build_script_folder="Configure")
        cmake.build()
        configure_args = load(self, os.path.join(self.generators_folder, "configure_args"))
        self.run(f"configure.exe {configure_args}", cwd=os.path.join(self.source_folder, "Configure"))

        self._patch_sources_msvc()
        msbuild = MSBuild(self)
        msbuild.build(os.path.join(self.source_folder, "IM7.Dynamic.sln"))

    def _generate_autotools(self):
        def yes_no(o):
            return "yes" if o else "no"

        gtc = GnuToolchain(self)

        tc = AutotoolsToolchain(self)
        tc.configure_args = [
            "--prefix=/",
            "--disable-openmp",
            "--disable-docs",
            "--with-perl=no",
            "--with-x=no",
            "--with-fontconfig=no",
            "--enable-shared={}".format(yes_no(self.options.shared)),
            "--enable-static={}".format(yes_no(not self.options.shared)),
            "--enable-hdri={}".format(yes_no(self.options.hdri)),
            "--with-quantum-depth={}".format(self.options.quantum_depth),
            "--with-zlib={}".format(yes_no(self.options.with_zlib)),
            "--with-bzlib={}".format(yes_no(self.options.with_bzlib)),
            "--with-lzma={}".format(yes_no(self.options.with_lzma)),
            "--with-lcms={}".format(yes_no(self.options.with_lcms)),
            "--with-openexr={}".format(yes_no(self.options.with_openexr)),
            "--with-heic={}".format(yes_no(self.options.with_heic)),
            "--with-jbig={}".format(yes_no(self.options.with_jbig)),
            "--with-jpeg={}".format(yes_no(self.options.with_jpeg)),
            "--with-openjp2={}".format(yes_no(self.options.with_openjp2)),
            "--with-pango={}".format(yes_no(self.options.with_pango)),
            "--with-png={}".format(yes_no(self.options.with_png)),
            "--with-tiff={}".format(yes_no(self.options.with_tiff)),
            "--with-webp={}".format(yes_no(self.options.with_webp)),
            "--with-xml={}".format(yes_no(self.options.with_xml2)),
            "--with-freetype={}".format(yes_no(self.options.with_freetype)),
            "--with-djvu={}".format(yes_no(self.options.with_djvu)),
            "--with-utilities={}".format(yes_no(self.options.utilities)),
            "--build={}".format(gtc.triplets_info["build"]["triplet"]),
            "--host={}".format(gtc.triplets_info["host"]["triplet"]),
        ]
        tc.generate()

        deps = AutotoolsDeps(self)
        # FIXME: workaround for xorg/system adding system includes https://github.com/conan-io/conan-center-index/issues/6880
        # if "/usr/include/uuid" in tc.include_paths:
        #     tc.include_paths.remove("/usr/include/uuid")
        deps.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def _build_autotools(self):
        with chdir(self, os.path.join(self.source_folder, "ImageMagick")):
            autotools = Autotools(self)
            autotools.configure(build_script_folder="ImageMagick")
            autotools.make()

    def generate(self):
        if is_msvc(self):
            self._generate_msvc()
        else:
            self._generate_autotools()

    def build(self):
        if is_msvc(self):
            self._build_msvc()
        else:
            self._build_autotools()

    def package(self):
        copy(self, "LICENSE", os.path.join(self.source_folder, "ImageMagick"), os.path.join(self.package_folder, "licenses"))
        if is_msvc(self):
            output_dir = os.path.join(self.source_folder, "Output")
            copy(self, "NOTICE.txt", output_dir, os.path.join(self.package_folder, "licenses"))
            copy(self, "*.dll", os.path.join(output_dir, "bin"), os.path.join(self.package_folder, "bin"))
            copy(self, "*.exe", os.path.join(output_dir, "bin"), os.path.join(self.package_folder, "bin"))
            copy(self, "*.lib", os.path.join(output_dir, "lib"), os.path.join(self.package_folder, "lib"))
            copy(self, "*.xml", os.path.join(output_dir, "bin"), os.path.join(self.package_folder, "share", self.name))
            copy(self, "*.icc", os.path.join(output_dir, "bin"), os.path.join(self.package_folder, "share", self.name))
            include_dir = os.path.join(self.package_folder, "include", f"ImageMagick-{Version(self.version).major}")
            copy(self, "*.h", os.path.join(self.source_folder, "ImageMagick", "MagickCore"), os.path.join(include_dir, "MagickCore"))
            copy(self, "*.h", os.path.join(self.source_folder, "ImageMagick", "MagickWand"), os.path.join(include_dir, "MagickWand"))
            copy(self, "*.h", os.path.join(self.source_folder, "ImageMagick", "Magick++", "lib"), include_dir)
        else:
            with chdir(self, os.path.join(self.source_folder, "ImageMagick")):
                autotools = Autotools(self)
                autotools.install()
            with chdir(self, self.package_folder):
                # remove undesired files
                rmdir(self, os.path.join("lib", "pkgconfig"))  # pc files
                rmdir(self, "etc")
                rm(self, "*.la", "lib", recursive=True)

    def _libname(self, library):
        if is_msvc(self):
            infix = "DB" if self.settings.build_type == "Debug" else "RL"
            return f"CORE_{infix}_{library}_"
        else:
            suffix = "HDRI" if self.options.hdri else ""
            return f"{library}-{Version(self.version).major}.Q{self.options.quantum_depth}{suffix}"

    def package_info(self):
        # FIXME model official FindImageMagick https://cmake.org/cmake/help/latest/module/FindImageMagick.html

        core_requires = []
        if self.options.with_zlib:
            core_requires.append("zlib-ng::zlib-ng")
        if self.options.with_bzlib:
            core_requires.append("bzip2::bzip2")
        if self.options.with_lzma:
            core_requires.append("xz_utils::xz_utils")
        if self.options.with_lcms:
            core_requires.append("lcms::lcms")
        if self.options.with_openexr:
            core_requires.append("openexr::openexr")
        if self.options.with_heic:
            core_requires.append("libheif::libheif")
        if self.options.with_jbig:
            core_requires.append("jbig::jbig")
        if self.options.with_jpeg:
            core_requires.append("{0}::{0}".format(self.options.with_jpeg))
        if self.options.with_openjp2:
            core_requires.append("openjpeg::openjpeg")
        if self.options.with_pango:
            core_requires.append("pango::pango")
        if self.options.with_png:
            core_requires.append("libpng::libpng")
        if self.options.with_tiff:
            core_requires.append("libtiff::libtiff")
        if self.options.with_webp:
            core_requires.append("libwebp::libwebp")
        if self.options.with_xml2:
            core_requires.append("libxml2::libxml2")
        if self.options.with_freetype:
            core_requires.append("freetype::freetype")
        if self.options.with_djvu:
            core_requires.append("djvulibre::djvulibre")

        if is_msvc(self) and not self.options.shared:
            self.cpp_info.components["MagickCore"].libs.append(self._libname("coders"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["MagickCore"].system_libs.append("pthread")

        self.cpp_info.components["MagickCore"].defines.append(f"MAGICKCORE_QUANTUM_DEPTH={self.options.quantum_depth}")
        self.cpp_info.components["MagickCore"].defines.append(f"MAGICKCORE_HDRI_ENABLE={int(bool(self.options.hdri))}")
        self.cpp_info.components["MagickCore"].defines.append("_MAGICKDLL_=1" if self.options.shared else "_MAGICKLIB_=1")

        include_dir_root = os.path.join("include", f"ImageMagick-{Version(self.version).major}")
        self.cpp_info.components["MagickCore"].includedirs = [include_dir_root]
        self.cpp_info.components["MagickCore"].libs.append(self._libname("MagickCore"))
        self.cpp_info.components["MagickCore"].requires = core_requires
        self.cpp_info.components["MagickCore"].set_property("pkg_config_name", "MagicCore")

        self.cpp_info.components[self._libname("MagickCore")].requires = ["MagickCore"]
        self.cpp_info.components[self._libname("MagickCore")].set_property("pkg_config_name", self._libname("MagickCore"))

        self.cpp_info.components["MagickWand"].includedirs = [os.path.join(include_dir_root, "MagickWand")]
        self.cpp_info.components["MagickWand"].libs = [self._libname("MagickWand")]
        self.cpp_info.components["MagickWand"].requires = ["MagickCore"]
        self.cpp_info.components["MagickWand"].set_property("pkg_config_name", "MagickWand")

        self.cpp_info.components[self._libname("MagickWand")].requires = ["MagickWand"]
        self.cpp_info.components[self._libname("MagickWand")].set_property("pkg_config_name", "MagickWand")

        self.cpp_info.components["Magick++"].includedirs = [os.path.join(include_dir_root, "Magick++")]
        self.cpp_info.components["Magick++"].libs = [self._libname("Magick++")]
        self.cpp_info.components["Magick++"].requires = ["MagickWand"]
        self.cpp_info.components["Magick++"].set_property("pkg_config_name", ["Magick++", self._libname("Magick++")])

        self.cpp_info.components[self._libname("Magick++")].requires = ["Magick++"]
        self.cpp_info.components[self._libname("Magick++")].set_property("pkg_config_name", self._libname("Magick++"))
