import glob
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, valid_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class CernRootConan(ConanFile):
    name = "cern-root"
    description = "CERN ROOT data analysis framework."
    license = "LGPL-2.1-or-later"
    # ROOT itself is located at: https://github.com/root-project/root
    homepage = "https://root.cern/"
    topics = ("data-analysis", "physics")

    # Don't allow static build as it is not supported
    # see: https://sft.its.cern.ch/jira/browse/ROOT-6446
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
        "asimage": [True, False],
        # FIXME: add option to use CCI Python package
        "python": ["off", "system"],
    }
    default_options = {
        "fPIC": True,
        "asimage": False,  # FIXME: requires builtin_afterimage, but its build is broken
        "python": "off",
    }
    options_description = {
        "asimage": "Enable support for image processing via libAfterImage",
        "python": "Enable support for automatic Python bindings (PyROOT)",
    }

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("arrow/17.0.0")
        self.requires("cfitsio/[^4.4.0]")
        self.requires("fftw/[^3.3.10]")
        self.requires("freetype/[^2.13.2]")
        self.requires("glew/2.2.0")
        self.requires("gsl/[^2.8]")
        self.requires("libcurl/[>=7.78 <9]")
        self.requires("libmysqlclient/[^8.1.0]")
        self.requires("libpq/[^17.0]")
        self.requires("libxml2/[^2.12.5]")
        self.requires("lz4/[^1.9.4]")
        self.requires("odbc/[^2.3.11]")
        self.requires("onetbb/[^2020.3]")
        self.requires("blas/latest")
        self.requires("opengl/system")
        self.requires("openssl/[>=1.1 <4]")
        self.requires("pcre/[^8.45]")
        self.requires("sqlite3/3.46.1")
        self.requires("xxhash/[>=0.8.1 <0.9]")
        self.requires("xz_utils/[^5.4.5]")
        self.requires("zlib-ng/[^2.0]")
        self.requires("zstd/[~1.5]")

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.requires("xorg/system")
            self.requires("libxft/[^2.3.8]")
            self.requires("libxpm/[^3.5.17]")
            self.requires("util-linux-libuuid/[^2.41]")

        if self.options.asimage:
            self.requires("giflib/[^5.2.1]")
            self.requires("libjpeg-meta/latest")
            self.requires("libpng/[~1.6]")
            self.requires("libtiff/4.6.0")

    def validate(self):
        # The project sets 11, but fails with compilation errors if 14 is not used
        check_min_cppstd(self, 14)

        libcxx = self.settings.get_safe("compiler.libcxx")
        # ROOT doesn't currently build with libc++.
        # This restriction may be lifted in future if the problems are fixed upstream
        if libcxx and libcxx == "libc++":
            raise ConanInvalidConfiguration(f'{self.name} is incompatible with libc++".')

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt",
                        "set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/modules)",
                        "list(APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake/modules)")
        # Fix execute permissions on scripts
        for pattern in ["**/configure", "**/*.sh", "**/*.csh", "**/*.bat",]:
            for filename in glob.glob(pattern, recursive=True):
                self._make_file_executable(filename)
        # Relax TBB version check
        replace_in_file(self, "cmake/modules/SearchInstalledSoftware.cmake", "TBB 2018", "TBB")
        rm(self, "Find*.cmake", "cmake/modules")
        # Let Conan set the C++ standard
        replace_in_file(self, "cmake/modules/CheckCompiler.cmake",
                        'set(CMAKE_CXX_STANDARD 11 CACHE STRING "")\n', "")

    @staticmethod
    def _make_file_executable(filename):
        st = os.stat(filename)
        os.chmod(filename, st.st_mode | stat.S_IEXEC)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_PROJECT_ROOT_INCLUDE"] = "conan_deps.cmake"
        if not valid_min_cppstd(self, self._minimum_cpp_standard):
            tc.variables["CMAKE_CXX_STANDARD"] = self._minimum_cpp_standard
        tc.variables["BUILD_SHARED_LIBS"] = True
        # Configure build options found at
        # https://github.com/root-project/root/blob/v6-22-06/cmake/modules/RootBuildOptions.cmake#L80-L193
        tc.variables["shared"] = True
        tc.variables["asimage"] = self.options.asimage
        tc.variables["fail-on-missing"] = True
        tc.variables["soversion"] = True
        tc.variables["x11"] = self.settings.os in ["Linux", "FreeBSD"]
        # Disable builtins and use Conan deps where available
        tc.variables["builtin_cfitsio"] = False
        tc.variables["builtin_davix"] = False
        tc.variables["builtin_fftw3"] = False
        tc.variables["builtin_freetype"] = False
        tc.variables["builtin_glew"] = False
        tc.variables["builtin_gsl"] = False
        tc.variables["builtin_lz4"] = False
        tc.variables["builtin_lzma"] = False
        tc.variables["builtin_openssl"] = False
        tc.variables["builtin_pcre"] = False
        tc.variables["builtin_tbb"] = False
        tc.variables["builtin_xxhash"] = False
        tc.variables["builtin_zlib"] = False
        tc.variables["builtin_zstd"] = False
        # Enable builtins where there is no Conan package
        tc.variables["builtin_afterimage"] = self.options.asimage  # FIXME : replace with afterimage CCI package when available
        tc.variables["builtin_gl2ps"] = True  # FIXME : replace with gl2ps CCI package when available
        tc.variables["builtin_ftgl"] = True  # FIXME : replace with ftgl CCI package when available
        tc.variables["builtin_vdt"] = True  # FIXME : replace with vdt CCI package when available
        tc.variables["builtin_clang"] = True
        tc.variables["builtin_llvm"] = True
        # Enable optional dependencies
        tc.variables["arrow"] = True
        tc.variables["mysql"] = True
        tc.variables["odbc"] = True
        tc.variables["pgsql"] = True
        # No Conan packages available for these dependencies yet
        tc.variables["davix"] = False  # FIXME : switch on if davix CCI package available
        tc.variables["pythia6"] = False  # FIXME : switch on if pythia6 CCI package available
        tc.variables["pythia8"] = False  # FIXME : switch on if pythia8 CCI package available
        tc.variables["oracle"] = False
        tc.variables["gfal"] = False  # FIXME: switch on if gfal CCI package available
        tc.variables["tmva-pymva"] = False  # FIXME: switch on if Python CCI package available
        tc.variables["xrootd"] = False  # FIXME: switch on if xrootd CCI package available
        tc.variables["pyroot"] = self._cmake_pyrootopt
        # clad is built with ExternalProject_Add and its
        # COMPILE_DEFINITIONS property is not propagated causing the build to
        # fail on some systems if libcxx != libstdc++11
        tc.variables["clad"] = False
        # Configure install directories
        # Conan CCI hooks restrict the allowed install directory
        # names but ROOT is very picky about where build/runtime
        # resources get installed.
        # Set install prefix to work around these limitations
        # Following: https://github.com/conan-io/conan/issues/3695
        tc.variables["CMAKE_INSTALL_CMAKEDIR"] = "lib/cmake"
        tc.variables["CMAKE_INSTALL_DATAROOTDIR"] = "share"
        tc.variables["CMAKE_INSTALL_SYSCONFDIR"] = "etc"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Python2"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Python3"] = self.options.python == "off"
        tc.generate()

        cmake_pkgs = {
            "arrow": "Arrow",
            "blas": "BLAS",
            "cfitsio": "CFITSIO",
            "fftw": "FFTW",
            "freetype": "Freetype",
            "giflib": "GIF",
            "glew": "GLEW",
            "gsl": "GSL",
            "libcurl": "CURL",
            "libjpeg": "JPEG",
            "libmysqlclient": "MySQL",
            "libpng": "PNG",
            "libpq": "PostgreSQL",
            "libxml2": "LibXml2",
            "libxft": "X11_Xft",
            "libxpm": "X11_Xpm",
            "lz4": "LZ4",
            "odbc": "ODBC",
            "onetbb": "TBB",
            "openssl": "OpenSSL",
            "pcre": "PCRE",
            "sqlite3": "Sqlite",
            "tiff": "TIFF",
            "xxhash": "xxHash",
            "xz_utils": "LibLZMA",
            "zlib": "ZLIB",
            "zstd": "ZSTD",
            # "afterimage": "AfterImage",
            # "alien": "Alien",
            # "cuda": "CUDA",
            # "cudnn": "CuDNN",
            # "davix": "Davix",
            # "dcap": "DCAP",
            # "fastcgi": "FastCGI",
            # "ftgl": "FTGL",
            # "gfal": "GFAL",
            # "gl2ps": "gl2ps",
            # "graphviz": "Graphviz",
            # "jemalloc": "jemalloc",
            # "monalisa": "Monalisa",
            # "mpi": "MPI",
            # "oracle": "Oracle",
            # "pythia6": "Pythia6",
            # "pythia8": "Pythia8",
            # "r": "R",
            # "tcmalloc": "tcmalloc",
            # "unuran": "Unuran",
            # "vc": "Vc",
            # "vdt": "Vdt",
            # "veccore": "VecCore",
            # "vecgeom": "VecGeom",
            # "xrootd": "XROOTD",
        }

        tc = CMakeDeps(self)
        for package, cmake_name in cmake_pkgs.items():
            tc.set_property(package, "cmake_file_name", cmake_name)
        tc.set_property("freetype", "cmake_target_name", "FreeType::FreeType")
        tc.set_property("pcre", "cmake_target_name", "PCRE::PCRE")
        tc.set_property("xxhash", "cmake_target_name", "xxHash::xxHash")
        tc.set_property("lz4", "cmake_target_name", "LZ4::LZ4")
        tc.generate()

    @property
    def _cmake_pyrootopt(self):
        return self.options.python != "off"

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Fix for CMAKE-MODULES-CONFIG-FILES (KB-H016)
        rm(self, "*Config*.cmake", os.path.join(self.package_folder, "lib", "cmake"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "share", "README"))
        rmdir(self, os.path.join(self.package_folder, "share", "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "share", "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "tutorials"))

    def package_info(self):
        # FIXME: ROOT generates multiple CMake files
        self.cpp_info.set_property("cmake_file_name", "ROOT")
        self.cpp_info.set_property("cmake_target_name", "ROOT::ROOT")

        # See root-config --libs for a list of ordered libs
        self.cpp_info.libs = [
            "Core",
            "Imt",
            "RIO",
            "Net",
            "Hist",
            "Graf",
            "Graf3d",
            "Gpad",
            "ROOTVecOps",
            "Tree",
            "TreePlayer",
            "Rint",
            "Postscript",
            "Matrix",
            "Physics",
            "MathCore",
            "Thread",
            "MultiProc",
            "ROOTDataFrame",
        ]
        self.cpp_info.resdirs = ["share"]

        build_modules = [
            os.path.join("lib", "cmake", "RootMacros.cmake"),
            # os.path.join("lib", "cmake", "ROOTUseFile.cmake"),
        ]
        self.cpp_info.set_property("cmake_build_modules", build_modules)
