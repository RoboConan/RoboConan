import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class GmpEcmConan(ConanFile):
    name = "gmp-ecm"
    description = "GMP-ECM: integer factorization using the Elliptic Curve Method, P-1 and P+1"
    license = "LGPL-3.0-or-later"
    homepage = "https://gitlab.inria.fr/zimmerma/ecm"
    topics = ("math", "factorization", "elliptic-curve", "number-theory")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "openmp": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("gmp/[^6.3.0]", transitive_headers=True, transitive_libs=True)
        if self.options.openmp:
            self.requires("openmp/system")

    def validate(self):
        # Upstream ships a separate MSVC project that.
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not yet supported")

    def build_requirements(self):
        self.tool_requires("libtool/[^2.4.7]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")

        def yes_no(v): return "yes" if v else "no"
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--with-gmp={unix_path(self, self.dependencies['gmp'].package_folder)}")
        tc.configure_args.append(f"--enable-openmp={yes_no(self.options.openmp)}")
        # Don't import CC/CFLAGS from gmp.h - use Conan's toolchain instead.
        tc.configure_args.append("--disable-gmp-cflags")
        tc.generate()

        tc = AutotoolsDeps(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LIB", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.libs = ["ecm"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread", "m"]
