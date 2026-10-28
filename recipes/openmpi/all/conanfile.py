import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, GnuToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.18"


class OpenMPIConan(ConanFile):
    name = "openmpi"
    description = "A High Performance Message Passing Library"
    license = "BSD-3-Clause"
    homepage = "https://www.open-mpi.org"
    topics = ("mpi", "openmpi", "hpc")
    provides = ["mpi"]
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "cuda", "fortran"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "fortran": ["yes", "mpifh", "usempi", "usempi80", "no"],
        "with_cuda": [True, False],
        "with_libfabric": [True, False],
        "with_ucx": [True, False],
        "with_oneapi": [True, False],
        # Removed in v5.0
        "enable_cxx": [True, False],
        "enable_cxx_exceptions": [True, False],
        "with_verbs": [True, False],
        "with_xpmem": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "fortran": "no",
        "with_cuda": False,
        "with_libfabric": True,
        "with_ucx": False,
        "with_oneapi": False,
        # Removed in v5.0
        "enable_cxx": False,
        "enable_cxx_exceptions": False,
        "with_verbs": False,
        "with_xpmem": False,
    }

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if Version(self.version) >= "5.0":
            # No longer used in v5.0
            del self.options.with_verbs
            del self.options.with_xpmem
            # The C++ bindings were deprecated in v2.2, removed from the standard in v3.0
            # and were removed from the implementation in v5.0.
            del self.options.enable_cxx
            del self.options.enable_cxx_exceptions

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.get_safe("enable_cxx"):
            self.settings.rm_safe("compiler.libcxx")
            self.settings.rm_safe("compiler.cppstd")
            self.options.rm_safe("enable_cxx_exceptions")
        if self.options.fortran == "no":
            self.settings.rm_safe("fortran")
        if is_apple_os(self):
            # Unavailable due to dependency on libnl
            self.options.rm_safe("with_verbs")
        if self.options.with_cuda:
            self.options["hwloc"].with_cuda = True
            if self.options.with_ucx:
                self.options["openucx"].with_cuda = True
        else:
            del self.settings.cuda
        if self.options.with_oneapi:
            self.options["hwloc"].with_oneapi = True
            if self.options.with_ucx:
                self.options["openucx"].ze = True
        if self.options.with_libfabric:
            if self.options.with_cuda:
                self.options["libfabric"].cuda = True
            if self.options.with_ucx:
                self.options["libfabric"].ucx = True
            if self.options.with_oneapi:
                self.options["libfabric"].ze = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        if self.info.options.with_cuda:
            # No need to embed CUDA version and architectures in package ID.
            del self.info.settings.cuda

    def requirements(self):
        # OpenMPI public headers don't include anything besides stddef.h.
        # transitive_headers=True is not needed for any dependencies.
        self.requires("hwloc/[^2.11.1]")
        self.requires("zlib-ng/[^2.0]")
        self.requires("libevent/[^2.1.12]")
        self.requires("openpmix/[<7]")
        if Version(self.version) >= "5.0":
            self.requires("prrte/[<5]")
        if self.settings.os == "Linux":
            self.requires("libnl/[^3.8.0]")
        if self.options.with_libfabric:
            self.requires("libfabric/[>=1.21.0 <3]")
        if self.options.get_safe("with_verbs"):
            self.requires("rdma-core/[*]")
        if self.options.get_safe("with_xpmem"):
            self.requires("xpmem/[^2.6.5]")
        if self.options.with_ucx:
            self.requires("openucx/[^1.19.0]")
        if self.options.with_cuda:
            self.requires(f"cuda-driver-stubs/[~{self.settings.cuda.version}]")
        if self.options.with_oneapi:
            self.requires("level-zero/[1.17.39]", force=True)
        if self.options.fortran != "no":
            self.fortran.requires_runtime()

    def validate(self):
        if self.settings.os == "Windows":
            # Requires Cygwin or WSL
            raise ConanInvalidConfiguration("OpenMPI doesn't support Windows")
        if self.options.fortran != "no":
            self.fortran.validate_settings()

    def validate_build(self):
        if self.options.fortran != "no":
            self.fortran.validate_build()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        if Version(self.version) >= "5.0":
            rmdir(self, "3rd-party/openpmix")
            rmdir(self, "3rd-party/prrte")
            rm(self, "hwloc-*", "3rd-party")
            rm(self, "libevent-*", "3rd-party")
        else:
            rmdir(self, "opal/mca/event/libevent2022/libevent")
            rmdir(self, "opal/mca/pmix/pmix3x/pmix")

    def generate(self):
        def root(pkg):
            return unix_path(self, self.dependencies[pkg].package_folder)

        def yes_no(v):
            return "yes" if v else "no"

        tc = GnuToolchain(self)
        tc.configure_args["--with-pic"] = self.options.get_safe("fPIC")
        tc.configure_args["--enable-mpi-fortran"] = self.options.fortran
        tc.configure_args["--enable-oshmem"] = yes_no(self.options.with_ucx)
        tc.configure_args["--with-cuda"] = root("cuda-driver-stubs") if self.options.with_cuda else "no"
        tc.configure_args["--with-hwloc"] = root("hwloc")
        tc.configure_args["--with-libevent"] = root("libevent")
        tc.configure_args["--with-libnl"] = root("libnl") if not is_apple_os(self) else "no"
        tc.configure_args["--with-ofi"] = root("libfabric") if self.options.with_libfabric else "no"
        tc.configure_args["--with-ucx"] = root("openucx") if self.options.with_ucx else "no"
        tc.configure_args["--with-zlib"] = root("zlib-ng")
        tc.configure_args["--with-pmix"] = root("openpmix")
        tc.configure_args["--with-treematch"] = "yes"  # internal
        tc.configure_args["--enable-wrapper-rpath"] = "no"
        tc.configure_args["--enable-wrapper-runpath"] = "no"
        tc.configure_args["--exec-prefix"] = "/"
        # Disable other external libraries explicitly
        tc.configure_args["--with-gpfs"] = "no"  # Gpfs
        tc.configure_args["--with-hcoll"] = "no"  # hcoll
        tc.configure_args["--with-ime"] = "no"  # IME
        tc.configure_args["--with-lsf"] = "no"  # LSF
        tc.configure_args["--with-lustre"] = "no"  # Lustre
        tc.configure_args["--with-memkind"] = "no"  # memkind
        tc.configure_args["--with-portals4"] = "no"  # Portals4
        tc.configure_args["--with-psm2"] = "no"  # PSM2
        tc.configure_args["--with-pvfs2"] = "no"  # Pvfs2
        tc.configure_args["--with-valgrind"] = "no"  # Valgrind
        if Version(self.version) >= "5.0":
            tc.configure_args["--with-prrte"] = root("prrte")  # PMIx runtime
            tc.configure_args["--enable-sphinx"] = "no"  # only used for docs
            tc.configure_args["--with-argobots"] = "no"  # argobots
            tc.configure_args["--with-libev"] = "no"  # not compatible with libevent, which cannot be disabled as of v5.0.5
            tc.configure_args["--with-munge"] = "no"  # munge
            tc.configure_args["--with-qthreads"] = "no"  # QThreads
        else:
            tc.configure_args["--enable-mpi-cxx"] = yes_no(self.options.enable_cxx)
            tc.configure_args["--enable-cxx-exceptions"] = yes_no(self.options.get_safe("enable_cxx_exceptions"))
            tc.configure_args["--with-verbs"] = root("rdma-core") if self.options.get_safe("with_verbs") else "no"
            tc.configure_args["--with-xpmem"] = root("xpmem") if self.options.with_xpmem else "no"
            tc.configure_args["--with-alps"] = "no"  # ALPS
            tc.configure_args["--with-fca"] = "no"  # FCA
            tc.configure_args["--with-mxm"] = "no"  # Mellanox MXM
            tc.configure_args["--with-pmi"] = "no"  # PMI
            tc.configure_args["--with-psm"] = "no"  # PSM
            tc.configure_args["--with-x"] = "no"  # X11
        if is_apple_os(self):
            if self.settings.arch == "armv8":
                tc.configure_args["--host"] = "aarch64-apple-darwin"
                tc.extra_ldflags.append("-arch arm64")
            # macOS has no libnl
            tc.configure_args["--enable-mca-no-build"] = "reachable-netlink"
        # libtool's libltdl is not really needed, OpenMPI provides its own equivalent.
        # Not adding it as it fails to be detected by ./configure in some cases.
        # https://github.com/open-mpi/ompi/blob/v4.1.6/opal/mca/dl/dl.h#L20-L25
        tc.configure_args["--with-libltdl"] = "no"
        # Disable a PMIx linking check
        tc.configure_args["oac_cv_check_package_pmix_wrapper_compiler_static_libs"] = ""
        deps = AutotoolsDeps(self)
        env = deps.environment.vars(self)
        # Linking of static transitive deps for tools is broken without this
        tc.make_args["LIBS"] = f'{env["LDFLAGS"]} {env["LIBS"]}'
        deps.generate()
        tc.generate()

        # Needed for ./configure to find libhwloc.so and libibnetdisc.so
        VirtualRunEnv(self).generate(scope="build")

        # TODO: might want to enable reproducible builds by setting
        #  $SOURCE_DATE_EPOCH, $USER and $HOSTNAME

    def _patch_sources(self):
        # Not needed and fails with v5.0 due to additional Python dependencies
        save(self, os.path.join(self.source_folder, "docs", "Makefile.in"), "all:\ninstall:\n")
        # Workaround for <cstddef> trying to include VERSION from source dir due to a case-insensitive filesystem on macOS
        # Based on https://github.com/macports/macports-ports/blob/22dded99ae76a287f04a9685bbc820ecaa397fea/science/openmpi/files/patch-configure.diff
        if Version(self.version) >= "5.0":
            replace_in_file(self, os.path.join(self.source_folder, "configure"),
                            "-I$(srcdir) ", "-idirafter$(srcdir) ")
        else:
            replace_in_file(self, os.path.join(self.source_folder, "configure"),
                            "-I$(top_srcdir) ", "-idirafter$(top_srcdir) ")

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "etc"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rm(self, "*.la", self.package_folder, recursive=True)
        fix_apple_shared_install_name(self)

    def package_info(self):
        # Based on https://cmake.org/cmake/help/latest/module/FindMPI.html#variables-for-using-mpi
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "MPI")
        self.cpp_info.set_property("pkg_config_name", "none")
        # TODO: export a .cmake module to correctly set all variables set by CMake's FindMPI.cmake

        requires = [
            "hwloc::hwloc",
            "libevent::libevent",
            "zlib-ng::zlib-ng",
            "openpmix::openpmix",
        ]
        if self.settings.os == "Linux":
            requires.append("libnl::libnl")
        if self.options.with_libfabric:
            requires.append("libfabric::libfabric")
        if self.options.get_safe("with_verbs"):
            requires.extend(["rdma-core::libibverbs", "rdma-core::librdmacm"])
        if self.options.get_safe("with_xpmem"):
            requires.append("xpmem::xpmem")
        if self.options.with_ucx:
            requires.append("openucx::openucx")
        if self.options.with_cuda:
            requires.append("cuda-driver-stubs::cuda-driver-stubs")
        if self.options.with_oneapi:
            requires.append("level-zero::level-zero")

        # The components are modelled based on OpenMPI's pkg-config files
        self.cpp_info.components["ompi"].set_property("pkg_config_name", "ompi")
        self.cpp_info.components["ompi"].libs = ["mpi"]

        if Version(self.version) >= "5.0":
            self.cpp_info.components["ompi"].requires = ["prrte::prrte"]
            self.cpp_info.components["ompi"].requires.append("open-pal")
        else:
            self.cpp_info.components["orte"].set_property("pkg_config_name", "orte")
            self.cpp_info.components["orte"].libs = ["open-rte"]
            self.cpp_info.components["orte"].requires.append("open-pal")
            self.cpp_info.components["ompi"].requires = ["orte"]

        self.cpp_info.components["open-pal"].libs = ["open-pal"]
        self.cpp_info.components["open-pal"].includedirs.append(os.path.join("include", "openmpi"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["open-pal"].system_libs = ["m", "dl", "pthread", "rt", "util"]
        self.cpp_info.components["open-pal"].cflags = ["-pthread"]
        self.cpp_info.components["open-pal"].requires = requires

        if Version(self.version) < "5.0":
            self.cpp_info.components["ompitrace"].set_property("pkg_config_name", "ompitrace")
            self.cpp_info.components["ompitrace"].libs = ["ompitrace"]
            self.cpp_info.components["ompitrace"].requires = ["ompi"]

        self.cpp_info.components["ompi-c"].set_property("pkg_config_name", "ompi-c")
        self.cpp_info.components["ompi-c"].set_property("cmake_target_name", "MPI::MPI_C")
        self.cpp_info.components["ompi-c"].requires = ["ompi"]

        if self.options.get_safe("enable_cxx"):
            self.cpp_info.components["ompi-cxx"].set_property("pkg_config_name", "ompi-cxx")
            self.cpp_info.components["ompi-cxx"].set_property("cmake_target_name", "MPI::MPI_CXX")
            self.cpp_info.components["ompi-cxx"].libs = ["mpi_cxx"]
            self.cpp_info.components["ompi-cxx"].requires = ["ompi"]
            if self.options.enable_cxx_exceptions:
                self.cpp_info.components["orte"].cflags.append("-fexceptions")

        if self.options.fortran != "no":
            self.cpp_info.components["ompi-fort"].set_property("pkg_config_name", "ompi-fort")
            self.cpp_info.components["ompi-fort"].set_property("cmake_target_name", "MPI::MPI_Fortran")
            self.cpp_info.components["ompi-fort"].libs = ["mpi_mpifh"]
            self.cpp_info.components["ompi-fort"].requires = ["ompi"]
            self.fortran.add_runtime_to_cpp_info(self.cpp_info.components["ompi-fort"])
            # Aliases
            self.cpp_info.components["ompi-f77"].set_property("pkg_config_name", "ompi-f77")
            self.cpp_info.components["ompi-f77"].requires = ["ompi-fort"]
            self.cpp_info.components["ompi-f90"].set_property("pkg_config_name", "ompi-f90")
            self.cpp_info.components["ompi-f90"].requires = ["ompi-fort"]

        if self.options.with_ucx:
            self.cpp_info.components["oshmem"].set_property("pkg_config_name", "oshmem")
            self.cpp_info.components["oshmem"].set_property("pkg_config_aliases", ["oshmem-c", "oshmem-cxx", "oshmem-fort"])
            self.cpp_info.components["oshmem"].libs = ["oshmem"]
            self.cpp_info.components["oshmem"].requires = ["ompi", "openucx::openucx"]

        bin_folder = os.path.join(self.package_folder, "bin")
        # Prepend to PATH to avoid a conflict with system MPI
        self.runenv_info.prepend_path("PATH", bin_folder)
        self.runenv_info.define_path("MPI_BIN", bin_folder)
        self.runenv_info.define_path("MPI_HOME", self.package_folder)
        self.runenv_info.define_path("OPAL_PREFIX", self.package_folder)
        self.runenv_info.define_path("OPAL_EXEC_PREFIX", self.package_folder)
        self.runenv_info.define_path("OPAL_LIBDIR", os.path.join(self.package_folder, "lib"))
        self.runenv_info.define_path("OPAL_DATADIR", os.path.join(self.package_folder, "share"))
        self.runenv_info.define_path("OPAL_DATAROOTDIR", os.path.join(self.package_folder, "share"))
