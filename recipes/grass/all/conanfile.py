import os
from pathlib import Path

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class GrassConan(ConanFile):
    name = "grass"
    description = "GRASS - free and open-source geospatial processing engine"
    license = "GPL-2.0-or-later"
    homepage = "https://grass.osgeo.org/"
    topics = ("geospatial", "gis", "remote-sensing")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "i18n": [True, False],
        "with_bzlib": [True, False],
        "with_cairo": [True, False],
        "with_blas": [True, False],
        "with_fftw": [True, False],
        "with_freetype": [True, False],
        "with_geos": [True, False],
        "with_lapack": [True, False],
        "with_liblas": [True, False],
        "with_libpng": [True, False],
        "with_mysql": [False, "libmysqlclient", "mariadb-connector-c"],
        "with_netcdf": [True, False],
        "with_odbc": [True, False],
        "with_opengl": [True, False],
        "with_openmp": [True, False],
        "with_pdal": [True, False],
        "with_postgres": [True, False],
        "with_readline": [True, False],
        "with_sqlite": [True, False],
        "with_tiff": [True, False],
        "with_x11": [True, False],
        "with_zstd": [True, False],
    }
    default_options = {
        "i18n": False,
        "with_bzlib": False,
        "with_cairo": False,
        "with_blas": False,
        "with_fftw": True,  # Can't be disabled currently
        "with_freetype": True,  # Can't be disabled currently
        "with_geos": True,
        "with_lapack": False,
        "with_liblas": False,
        "with_libpng": True,
        "with_mysql": False,
        "with_netcdf": False,
        "with_odbc": False,
        "with_opengl": False,
        "with_openmp": True,
        "with_pdal": True,  # Can't be disabled currently
        "with_postgres": True,  # Can't be disabled currently
        "with_readline": False,
        "with_sqlite": True,  # Can't be disabled currently
        "with_tiff": True,
        "with_x11": False,
        "with_zstd": False,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        self.requires("gdal/[^3.5]", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg-meta/latest")
        self.requires("proj/[^9.3.1]", transitive_headers=True, transitive_libs=True)
        if is_apple_os(self):
            self.requires("libiconv/[^1.17]")
        if is_msvc(self):
            self.requires("pcre/[^8.45]")
        if self.options.with_bzlib:
            self.requires("bzip2/[^1.0.8]")
        if self.options.with_cairo:
            self.requires("cairo/[^1.18.0]")
        if self.options.with_blas:
            self.requires("blas/latest")
        if self.options.with_lapack:
            self.requires("lapack/latest")
        if self.options.with_fftw:
            self.requires("fftw/[^3.3.10]")
        if self.options.with_freetype:
            self.requires("freetype/[^2.12.1]")
        if self.options.with_geos:
            self.requires("geos/[^3.12.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_liblas:
            self.requires("liblas/[^1.8.1]")
        if self.options.with_libpng:
            self.requires("libpng/[~1.6]")
        if self.options.with_mysql == "libmysqlclient":
            self.requires("libmysqlclient/[^8.1.0]")
        elif self.options.with_mysql == "mariadb-connector-c":
            self.requires("mariadb-connector-c/[^3.3.3]")
        if self.options.with_netcdf:
            self.requires("netcdf/[^4.9.3]")
        if self.options.i18n:
            self.requires("gettext/[^0.21]", transitive_headers=True, transitive_libs=True)
        if self.options.with_odbc:
            self.requires("odbc/[^2.3.11]")
        if self.options.with_opengl:
            self.requires("opengl/system", transitive_headers=True)
        if self.options.with_openmp:
            self.requires("openmp/system", transitive_headers=True, transitive_libs=True)
        if self.options.with_pdal:
            self.requires("pdal/[^2.7.2]")
        if self.options.with_postgres:
            self.requires("libpq/[>=15.0]", transitive_headers=True)
        if self.options.with_readline:
            self.requires("readline/[^8.2]")
        if self.options.with_sqlite:
            self.requires("sqlite3/[^3.40]")
        if self.options.with_tiff:
            self.requires("libtiff/[^4.5.0]")
        if self.options.with_x11:
            self.requires("xorg/system", transitive_headers=True)
        if self.options.with_zstd:
            self.requires("zstd/[~1.5]")

    def validate(self):
        check_min_cppstd(self, 14)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.22 <5]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "lib/init/CMakeLists.txt", "get_filename_component(", "# get_filename_component(")
        # GEOS::geos_c is used by nearly all modules, but the dep is not propagated correctly
        replace_in_file(self, "cmake/modules/CheckDependentLibraries.cmake",
                        "find_package(GEOS REQUIRED)", "find_package(GEOS REQUIRED)\nlink_libraries(GEOS::geos_c)")
        # Don't manually create a target for liblas
        replace_in_file(self, "cmake/modules/CheckDependentLibraries.cmake", "if(LibLAS_FOUND)", "if(FALSE)")
        # No option to disable building of tests
        replace_in_file(self, "CMakeLists.txt", "enable_testing()", "")
        # Don't generate thumbnails, since it needs additional setup of runtime deps
        replace_in_file(self, "CMakeLists.txt", "r_colors_thumbnails ALL", "r_colors_thumbnails")
        replace_in_file(self, "CMakeLists.txt", "install(DIRECTORY ${OUTDIR}/${GRASS_INSTALL_DOCDIR}/colortables", "message(TRACE ")
        # FIXME Disable scripts subdir, installation of which is currently broken
        save(self, "scripts/CMakeLists.txt", "")
        # Disable g.mkfontcap call, which breaks cross-compilation
        replace_in_file(self, "general/CMakeLists.txt", "add_custom_command(", "message(TRACE ")
        replace_in_file(self, "general/CMakeLists.txt", "install(FILES ${OUTDIR}/${GRASS_INSTALL_ETCDIR}/fontcap", "message(TRACE ")

    def generate(self):
        tc = CMakeToolchain(self)
        # Graphics options
        tc.cache_variables["WITH_X11"] = self.options.with_x11
        tc.cache_variables["WITH_OPENGL"] = self.options.with_opengl
        tc.cache_variables["WITH_CAIRO"] = self.options.with_cairo
        tc.cache_variables["WITH_LIBPNG"] = self.options.with_libpng
        # Data storage options
        tc.cache_variables["WITH_SQLITE"] = self.options.with_sqlite
        tc.cache_variables["WITH_POSTGRES"] = self.options.with_postgres
        tc.cache_variables["WITH_MYSQL"] = bool(self.options.with_mysql)
        tc.cache_variables["WITH_ODBC"] = self.options.with_odbc
        tc.cache_variables["WITH_ZSTD"] = self.options.with_zstd
        tc.cache_variables["WITH_BZLIB"] = self.options.with_bzlib
        # Command-line options
        tc.cache_variables["WITH_READLINE"] = self.options.with_readline
        # Language options
        tc.cache_variables["WITH_FREETYPE"] = self.options.with_freetype
        tc.cache_variables["WITH_NLS"] = self.options.i18n
        # Computing options
        tc.cache_variables["WITH_FFTW"] = self.options.with_fftw
        tc.cache_variables["WITH_CBLAS"] = self.options.with_blas
        tc.cache_variables["WITH_LAPACKE"] = self.options.with_lapack
        tc.cache_variables["WITH_OPENMP"] = self.options.with_openmp
        # Data format options
        tc.cache_variables["WITH_TIFF"] = self.options.with_tiff
        tc.cache_variables["WITH_NETCDF"] = self.options.with_netcdf
        tc.cache_variables["WITH_GEOS"] = self.options.with_geos
        tc.cache_variables["WITH_PDAL"] = self.options.with_pdal
        tc.cache_variables["WITH_LIBLAS"] = self.options.with_liblas
        # Other options
        tc.cache_variables["WITH_LARGEFILES"] = True
        tc.cache_variables["WITH_DOCS"] = False
        tc.cache_variables["WITH_GUI"] = False
        tc.cache_variables["WITH_FHS"] = False
        tc.cache_variables["USE_CCACHE"] = False
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.cache_variables["HAVE_LAPACKE_DGESV"] = True
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0175"] = "OLD"
        tc.cache_variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("cairo", "cmake_target_name", "Cairo::Cairo")
        deps.set_property("geos", "cmake_file_name", "GEOS")
        deps.set_property("geos", "cmake_target_name", "GEOS::geos_c")
        deps.set_property("liblas", "cmake_file_name", "LibLAS")
        deps.set_property("liblas", "cmake_target_name", "LIBLAS")
        deps.set_property("blas", "cmake_file_name", "CBLAS")
        deps.set_property("blas", "cmake_target_name", "CBLAS::CBLAS")
        deps.set_property("lapack", "cmake_file_name", "LAPACKE")
        deps.set_property("lapack", "cmake_target_name", "LAPACKE::LAPACKE")
        deps.set_property("proj", "cmake_file_name", "PROJ")
        deps.set_property("proj", "cmake_target_name", "PROJ::proj")
        deps.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @property
    def _versioned_name(self):
        v = Version(self.version)
        return f"grass{v.major}{v.minor}"

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "GPL.TXT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        prefix = os.path.join("lib", self._versioned_name)
        for path in Path(self.package_folder, prefix).iterdir():
            if path.is_file():
                path.unlink()
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, prefix, "doc"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "grass")

        prefix = os.path.join("lib", self._versioned_name)
        self.cpp_info.bindirs = ["bin", os.path.join(prefix, "bin"), os.path.join(prefix, "scripts")]
        self.cpp_info.libdirs = [os.path.join(prefix, "lib")]
        self.cpp_info.includedirs = [os.path.join(prefix, "include"), os.path.join(prefix, "include", "export")]
        self.cpp_info.libs = collect_libs(self)

        self.runenv_info.define_path("GRASS_ADDON_BASE", os.path.join(self.package_folder, prefix))
