import os
import shutil

from conan import ConanFile
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps, PkgConfig
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, unix_path

required_conan_version = ">=2.1"


class CoinCouenneConan(ConanFile):
    name = "coin-couenne"
    description = ("Couenne (Convex Over and Under Envelopes for Nonlinear Estimation) is a"
                   " branch&bound algorithm to solve Mixed-Integer Nonlinear Programming (MINLP) problems")
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Couenne"
    topics = ("optimization", "mixed-integer-nonlinear-programming", "coin-or")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_nauty": [True, False],
        "with_scip": [True, False],
        "with_asl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_nauty": True,
        "with_scip": False,
        "with_asl": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("coin-bonmin/[^1.8.9]", transitive_headers=True, transitive_libs=True)
        self.requires("coin-osi/[>=0.108.10 <1]", transitive_headers=True, transitive_libs=True)
        if self.options.with_nauty:
            self.requires("nauty/[^2.9.1]", transitive_headers=True)
        if self.options.with_scip:
            self.requires("scip/[*]", transitive_headers=True, transitive_libs=True)
        if self.options.with_asl:
            self.requires("ampl-asl/[^1]")

    def build_requirements(self):
        self.tool_requires("coin-buildtools/[*]")
        self.tool_requires("gnu-config/[*]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Fortran's only needed for BLAS naming scheme detection. Don't look for it.
        replace_in_file(self, "Couenne/configure.ac", "AC_COIN_PROG_F77", "")
        replace_in_file(self, "Couenne/configure.ac", "AC_COIN_F77_WRAPPERS", "")

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
        deps.set_property("ampl-asl", "pkg_config_name", "coinasl")
        deps.set_property("scip", "pkg_config_name", "coinscip")
        deps.generate()

        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        osi = self.dependencies["coin-osi"]
        tc.configure_args += [
            f"--with-asl={yes_no(self.options.with_asl)}",
            f"--with-scip={yes_no(self.options.with_scip)}",
            f"--with-osicplex={yes_no(osi.options.with_cplex)}",
            f"--with-osigurobi={yes_no(osi.options.with_gurobi)}",
            f"--with-osimosek={yes_no(osi.options.with_mosek)}",
            f"--with-osisoplex={yes_no(osi.options.with_soplex)}",
            f"--with-osixpress={yes_no(osi.options.with_xpress)}",
            "F77=unavailable",
        ]

        if osi.options.with_cplex:
            _, ldflags = self._flags_from_pc("cplex")
            tc.configure_args.append(f"--with-cplex-incdir={unix_path(self, self.dependencies['cplex'].cpp_info.includedir)}/ilcplex")
            tc.configure_args.append(f"--with-cplex-lib={ldflags}")

        if self.options.with_nauty:
            nauty_info = self.dependencies["nauty"].cpp_info
            tc.configure_args.append(f"--with-nauty-lib=-l{nauty_info.libs[0]} -L{unix_path(self, nauty_info.libdir)}")
            tc.configure_args.append(f"--with-nauty-incdir={unix_path(self, nauty_info.includedir)}")

        # Drop deprecated `register` keywords
        tc.extra_cxxflags.append("-Dregister=")

        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
            tc.configure_args.append(f"--enable-msvc={msvc_runtime_flag(self)}")
        tc.generate()

        env = tc.environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        if is_msvc(self):
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("NM", "dumpbin -symbols")
            env.vars(self).save_script("conanbuild_msvc")
        tc.generate(env)

    def build(self):
        buildtools = self.dependencies.build["coin-buildtools"].cpp_info.resdirs[0]
        copy(self, "*", buildtools, os.path.join(self.source_folder, "Couenne", "BuildTools"))
        for gnu_config in ["config_guess", "config_sub"]:
            gnu_config = self.conf.get(f"user.gnu-config:{gnu_config}", check_type=str)
            shutil.copy(gnu_config, os.path.join(self.source_folder, "Couenne"))
        autotools = Autotools(self)
        autotools.autoreconf(build_script_folder="Couenne")
        autotools.configure(build_script_folder="Couenne")
        # Manually specify OpenBLAS naming scheme since F77 is not available to autodetect it.
        save(self, os.path.join(self.build_folder, "src/config.h"),
             "\n"
             "#define F77_FUNC(name,NAME) name ## _\n"
             "#define F77_FUNC_(name,NAME) name ## _\n",
             append=True)
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Installation script expects include/coin to already exist
        mkdir(self, os.path.join(self.package_folder, "include", "coin"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.components["libcouenne"].set_property("pkg_config_name", "couenne")
        self.cpp_info.components["libcouenne"].libs = ["Couenne"]
        self.cpp_info.components["libcouenne"].includedirs.append("include/coin")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libcouenne"].system_libs = ["m", "pthread", "rt", "dl"]
        self.cpp_info.components["libcouenne"].requires = [
            "coin-bonmin::coin-bonmin",
            "coin-osi::coin-osi",
        ]
        if self.options.with_nauty:
            self.cpp_info.components["libcouenne"].requires.append("nauty::nauty")
        if self.options.with_scip:
            self.cpp_info.components["libcouenne"].requires.append("scip::scip")

        if self.options.with_asl:
            self.cpp_info.components["couenneinterfaces"].set_property("pkg_config_name", "couenneinterfaces")  # unofficial
            self.cpp_info.components["couenneinterfaces"].libs = ["CouenneInterfaces"]
            self.cpp_info.components["couenneinterfaces"].includedirs.append("include/coin")
            self.cpp_info.components["couenneinterfaces"].requires = ["libcouenne", "ampl-asl::asl"]
