import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, PkgConfig
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class OctaveConan(ConanFile):
    name = "octave"
    description = "GNU Octave is a high-level language for numerical computations"
    license = "GPL-3.0-or-later"
    homepage = "https://www.octave.org"
    topics = ("scientific-computing", "matlab", "numerical-analysis", "mathematics")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_arpack": [True, False],
        "with_curl": [True, False],
        "with_glpk": [True, False],
        "with_hdf5": [True, False],
        "with_openmp": [True, False],
        "with_qhull": [True, False],
        "with_qrupdate": [True, False],
        "with_rapidjson": [True, False],
        "with_suitesparse": [True, False],
        "with_sundials": [True, False],
    }
    default_options = {
        "with_arpack": False,
        "with_curl": False,
        "with_glpk": False,
        "with_hdf5": False,
        "with_openmp": True,
        "with_qhull": False,
        "with_qrupdate": False,
        "with_rapidjson": True,
        "with_suitesparse": False,
        "with_sundials": False,
    }

    @property
    def _fortran_compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return executables.get("fortran")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        self.requires("fftw/[^3.3]")
        self.requires("pcre2/[^10]")
        self.requires("readline/[*]")
        self.requires("zlib-ng/[^2]")
        self.requires("bzip2/[^1.0.8]")

        if self.options.with_openmp:
            self.requires("openmp/system")
        if self.options.with_curl:
            self.requires("libcurl/[>=7.78 <9]")
        if self.options.with_hdf5:
            self.requires("hdf5/[^1.14]")
        if self.options.with_rapidjson:
            self.requires("rapidjson/[*]")
        if self.options.with_qhull:
            self.requires("qhull/[^8]")
        if self.options.with_glpk:
            self.requires("glpk/[^5]")
        if self.options.with_arpack:
            self.requires("arpack-ng/[^3]")
        if self.options.with_qrupdate:
            self.requires("qrupdate-ng/[^1]")
        if self.options.with_sundials:
            self.requires("sundials/[>=6 <8]")
        if self.options.with_suitesparse:
            self.requires("suitesparse-spqr/[^4]")
            self.requires("suitesparse-amd/[^3]")
            self.requires("suitesparse-camd/[^3]")
            self.requires("suitesparse-colamd/[^3]")
            self.requires("suitesparse-ccolamd/[^3]")
            self.requires("suitesparse-cholmod/[^5]")
            self.requires("suitesparse-cxsparse/[^4]")
            self.requires("suitesparse-klu/[^2]")
            self.requires("suitesparse-umfpack/[^6]")

    def validate(self):
        check_min_cppstd(self, 17)

    def validate_build(self):
        if not self._fortran_compiler:
            raise ConanInvalidConfiguration(
                "Octave requires a Fortran compiler to build. "
                "Please provide one by setting tools.build:compiler_executables={'fortran': '...'}."
            )

    def build_requirements(self):
        self.tool_requires("libtool/[^2.4.7]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Skip docs
        replace_in_file(self, "Makefile.am", "include doc/module.mk", "")

    def _flags_from_pc(self, name):
        pc = PkgConfig(self, name, self.generators_folder)
        cflags = list(pc.cflags)
        cflags += [f"-I{unix_path(self, inc)}" for inc in pc.includedirs]
        ldflags = list(pc.linkflags)
        ldflags += [f"-L{unix_path(self, libdir)}" for libdir in pc.libdirs]
        ldflags += [f"-l{lib}" for lib in pc.libs]
        return " ".join(cflags), " ".join(ldflags)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.set_property("qhull::libqhull_r", "pkg_config_name", "qhull_r")
        deps.generate()

        yes_no = lambda v: "yes" if v else "no"
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-docs",
            "--enable-year2038",
            "--enable-fortran-calling-convention=gfortran",
            "--enable-readline",
            f"--with-libreadline-prefix={unix_path(self, self.dependencies['readline'].package_folder)}",
            f"--enable-openmp={yes_no(self.options.with_openmp)}",
            f"--with-curl={yes_no(self.options.with_curl)}",
            f"--with-glpk={yes_no(self.options.with_glpk)}",
            f"--with-hdf5={yes_no(self.options.with_hdf5)}",
            f"--with-qhull_r={yes_no(self.options.with_qhull)}",
            f"--enable-rapidjson={yes_no(self.options.with_rapidjson)}",
            f"--with-fftw3={yes_no(self.dependencies['fftw'].options.precision_double)}",
            f"--with-fftw3f={yes_no(self.dependencies['fftw'].options.precision_single)}",
            "--with-z",
            "--with-bz2",
            "--with-pcre2",
            # FIXME: picks up system blas/lapack
            "--with-blas",
            "--with-lapack",

            f"--with-amd={yes_no(self.options.with_suitesparse)}",
            f"--with-camd={yes_no(self.options.with_suitesparse)}",
            f"--with-ccolamd={yes_no(self.options.with_suitesparse)}",
            f"--with-cholmod={yes_no(self.options.with_suitesparse)}",
            f"--with-colamd={yes_no(self.options.with_suitesparse)}",
            f"--with-cxsparse={yes_no(self.options.with_suitesparse)}",
            f"--with-klu={yes_no(self.options.with_suitesparse)}",
            f"--with-spqr={yes_no(self.options.with_suitesparse)}",
            f"--with-suitesparseconfig={yes_no(self.options.with_suitesparse)}",
            f"--with-umfpack={yes_no(self.options.with_suitesparse)}",

            f"--with-sundials_core={yes_no(self.options.with_sundials)}",
            f"--with-sundials_ida={yes_no(self.options.with_sundials)}",
            f"--with-sundials_nvecserial={yes_no(self.options.with_sundials)}",
            f"--with-sundials_sunlinsolklu={yes_no(self.options.with_sundials)}",

            f"--with-arpack={yes_no(self.options.with_arpack)}",
            f"--with-qrupdate={yes_no(self.options.with_qrupdate)}",

            "--without-pcre",
            "--without-sndfile",
            "--without-portaudio",
            "--without-magick",
            "--disable-java",

            # Disable GUI
            "--without-qt",
            "--without-qscintilla",
            "--without-x",
            "--without-fltk",
            "--without-opengl",
            "--without-freetype",
            "--without-fontconfig",
            "--without-framework-carbon",
            "--without-framework-opengl",
        ])

        def _configure_dep(var, pc_name):
            cflags, ldflags = self._flags_from_pc(pc_name)
            tc.configure_args.append(f"{var}_CPPFLAGS={cflags}")
            tc.configure_args.append(f"{var}_LDFLAGS={ldflags}")

        if self.options.with_sundials:
            _configure_dep("SUNDIALS_SUNLINSOLKLU", "sundials-sunlinsolklu")
            _configure_dep("SUNDIALS_CORE", "sundials-core")
            _configure_dep("SUNDIALS_IDA", "sundials-ida")
            _configure_dep("SUNDIALS_NVECSERIAL", "sundials-nvecserial")

        if self.options.with_qhull:
            _configure_dep("QHULL_R", "qhull_r")

        _configure_dep("Z", "zlib")

        env = tc.environment()
        if self.options.with_rapidjson:
            path = unix_path(self, self.dependencies["rapidjson"].cpp_info.includedir)
            env.append("CPPFLAGS", f"-I{path}", separator=" ")

        tc.generate(env)

    def build(self):
        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", self.package_folder, recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        v = Version(self.version)
        version_str = f"{v.major}.{v.minor}.{v.patch}"
        incdir = f"include/octave-{version_str}"
        libdir = f"lib/octave/{version_str}"

        # C++ interface to GNU Octave underlying library
        self.cpp_info.components["octave_"].set_property("pkg_config_name", "octave")
        self.cpp_info.components["octave_"].libs = ["octave"]
        self.cpp_info.components["octave_"].includedirs = [incdir, f"{incdir}/octave"]
        self.cpp_info.components["octave_"].libdirs = [libdir]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["octave_"].system_libs = ["m", "pthread", "dl", "rt"]

        # C++ interface to GNU Octave interpreter
        self.cpp_info.components["octinterp"].set_property("pkg_config_name", "octinterp")
        self.cpp_info.components["octinterp"].libs = ["octinterp"]
        self.cpp_info.components["octinterp"].includedirs = [incdir, f"{incdir}/octave"]
        self.cpp_info.components["octinterp"].libdirs = [libdir]
        self.cpp_info.components["octinterp"].requires = ["octave_"]

        # C interface (MEX) to GNU Octave interpreter
        self.cpp_info.components["octmex"].set_property("pkg_config_name", "octmex")
        self.cpp_info.components["octmex"].libs = ["octmex"]
        self.cpp_info.components["octmex"].includedirs = [incdir, f"{incdir}/octave"]
        self.cpp_info.components["octmex"].libdirs = [libdir]
        self.cpp_info.components["octmex"].requires = ["octave_", "octinterp"]

        requires = [
            "lapack::lapack",
            "fftw::fftw",
            "pcre2::pcre2",
            "readline::readline",
            "zlib-ng::zlib-ng",
            "bzip2::bzip2",
        ]
        if self.options.with_openmp:
            requires.append("openmp::openmp")
        if self.options.with_glpk:
            requires.append("glpk::glpk")
        if self.options.with_curl:
            requires.append("libcurl::libcurl")
        if self.options.with_hdf5:
            requires.append("hdf5::hdf5")
        if self.options.with_qhull:
            requires.append("qhull::qhull")
        if self.options.with_rapidjson:
            requires.append("rapidjson::rapidjson")
        if self.options.with_suitesparse:
            requires.extend([
                "suitesparse-spqr::suitesparse-spqr",
                "suitesparse-amd::suitesparse-amd",
                "suitesparse-camd::suitesparse-camd",
                "suitesparse-colamd::suitesparse-colamd",
                "suitesparse-ccolamd::suitesparse-ccolamd",
                "suitesparse-cholmod::suitesparse-cholmod",
                "suitesparse-cxsparse::suitesparse-cxsparse",
                "suitesparse-klu::suitesparse-klu",
                "suitesparse-umfpack::suitesparse-umfpack",
            ])
        if self.options.with_arpack:
            requires.append("arpack-ng::arpack-ng")
        if self.options.with_qrupdate:
            requires.append("qrupdate-ng::qrupdate-ng")
        if self.options.with_sundials:
            requires.append("sundials::sundials")
        self.cpp_info.components["octave_"].requires = requires
