import os
import re
import shutil
import textwrap

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class FreetypeConan(ConanFile):
    name = "freetype"
    description = "FreeType is a freely available software library to render fonts."
    license = "FTL"
    homepage = "https://www.freetype.org"
    topics = ("freetype", "fonts")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_png": [True, False],
        "with_zlib": [True, False],
        "with_bzip2": [True, False],
        "with_brotli": [True, False],
        "subpixel": [True, False],
        "error_strings": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_png": True,
        "with_zlib": True,
        "with_bzip2": True,
        "with_brotli": True,
        "subpixel": False,
        "error_strings": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_png:
            self.requires("libpng/[~1.6]")
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_bzip2:
            self.requires("bzip2/[^1.0.8]")
        if self.options.get_safe("with_brotli"):
            self.requires("brotli/[^1.1.0]")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        virtual_build_env = VirtualBuildEnv(self)
        virtual_build_env.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

        def feature(option):
            return "enabled" if option else "disabled"

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["brotli"] = feature(self.options.with_brotli)
        tc.project_options["bzip2"] = feature(self.options.with_bzip2)
        # Harfbuzz support introduces a circular dependency between Harfbuzz and Freetype.
        # They both have options to require each other.
        tc.project_options["harfbuzz"] = "disabled"
        tc.project_options["png"] = feature(self.options.with_png)
        tc.project_options["error_strings"] = self.options.error_strings
        tc.project_options["tests"] = "disabled"
        tc.project_options["zlib"] = "system" if self.options.with_zlib else "disabled"
        tc.generate()

    def _patch_sources(self):
        config_h = os.path.join(self.source_folder, "include", "freetype", "config", "ftoption.h")
        if self.options.subpixel:
            replace_in_file(self, config_h, "/* #define FT_CONFIG_OPTION_SUBPIXEL_RENDERING */", "#define FT_CONFIG_OPTION_SUBPIXEL_RENDERING")

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _make_freetype_config(self, version):
        freetype_config_in = os.path.join(self.source_folder, "builds", "unix", "freetype-config.in")
        if not os.path.isdir(os.path.join(self.package_folder, "bin")):
            os.makedirs(os.path.join(self.package_folder, "bin"))
        freetype_config = os.path.join(self.package_folder, "bin", "freetype-config")
        rename(self, freetype_config_in, freetype_config)
        staticlibs = "-lm -lfreetype" if self.settings.os == "Linux" else "-lfreetype"
        replace_in_file(self, freetype_config, r"%PKG_CONFIG%", r"/bin/false")  # never use pkg-config
        replace_in_file(self, freetype_config, r"%prefix%", r"$conan_prefix")
        replace_in_file(self, freetype_config, r"%exec_prefix%", r"$conan_exec_prefix")
        replace_in_file(self, freetype_config, r"%includedir%", r"$conan_includedir")
        replace_in_file(self, freetype_config, r"%libdir%", r"$conan_libdir")
        replace_in_file(self, freetype_config, r"%ft_version%", r"$conan_ftversion")
        replace_in_file(self, freetype_config, r"%LIBSSTATIC_CONFIG%", r"$conan_staticlibs")
        replace_in_file(self, freetype_config, r"export LC_ALL", textwrap.dedent("""\
            export LC_ALL
            BINDIR=$(dirname $0)
            conan_prefix=$(dirname $BINDIR)
            conan_exec_prefix=${{conan_prefix}}/bin
            conan_includedir=${{conan_prefix}}/include
            conan_libdir=${{conan_prefix}}/lib
            conan_ftversion={version}
            conan_staticlibs="{staticlibs}"
        """).format(version=version, staticlibs=staticlibs))

    def _extract_soversion(self):
        conf_raw = load(self, os.path.join(self.source_folder, "builds", "unix", "configure.raw"))
        return re.search(r"^version_info='([0-9:]+)'", conf_raw, flags=re.M).group(1).replace(":", ".")

    @property
    def _soversion_txt(self):
        return os.path.join(self.package_folder, "share", "conan", "freetype-soversion.txt")

    def package(self):
        meson = Meson(self)
        meson.install()

        ver = Version(self.version)
        if self.settings.os == "Windows" and self.options.shared and "2.13.0" <= ver < "2.14.0":
            # Duplicate DLL name for backwards compatibility with earlier recipe revisions
            # See https://github.com/conan-io/conan-center-index/issues/23768
            suffix = "d" if self.settings.build_type == "Debug" else ""
            prefix = "lib" if self.settings.compiler == "gcc" else ""  # For MinGW
            src = os.path.join(self.package_folder, "bin", f"{prefix}freetype-6.dll")
            dst = os.path.join(self.package_folder, "bin", f"{prefix}freetype{suffix}.dll")
            shutil.copyfile(src, dst)

        soversion = self._extract_soversion()
        save(self, self._soversion_txt, soversion)
        self._make_freetype_config(soversion)

        doc_folder = os.path.join(self.source_folder, "docs")
        license_folder = os.path.join(self.package_folder, "licenses")
        copy(self, "FTL.TXT", doc_folder, license_folder)
        copy(self, "GPLv2.TXT", doc_folder, license_folder)
        copy(self, "LICENSE.TXT", doc_folder, license_folder)

        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        save(self, os.path.join(self.package_folder, self._module_vars_rel_path), "set(FREETYPE_FOUND TRUE)\n")
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    @property
    def _module_vars_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-variables.cmake")

    @staticmethod
    def _chmod_plus_x(filename):
        if os.name == "posix" and (os.stat(filename).st_mode & 0o111) != 0o111:
            os.chmod(filename, os.stat(filename).st_mode | 0o111)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_module_file_name", "Freetype")
        self.cpp_info.set_property("cmake_file_name", "freetype")
        self.cpp_info.set_property("cmake_target_name", "Freetype::Freetype")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["FREETYPE"])
        self.cpp_info.set_property("cmake_target_aliases", ["freetype"]) # other possible target name in upstream config file
        self.cpp_info.set_property("cmake_build_modules", [self._module_vars_rel_path])
        self.cpp_info.set_property("pkg_config_name", "freetype2")
        self.cpp_info.libs = ["freetype"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
        self.cpp_info.includedirs.append(os.path.join("include", "freetype2"))

        soversion = load(self, self._soversion_txt).strip()
        self.cpp_info.set_property("system_package_version", soversion)

        freetype_config = os.path.join(self.package_folder, "bin", "freetype-config")
        self._chmod_plus_x(freetype_config)
