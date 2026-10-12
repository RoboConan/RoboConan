import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, NMakeDeps, NMakeToolchain

required_conan_version = ">=2.4"


class LibrasterliteConan(ConanFile):
    name = "librasterlite"
    description = (
        "librasterlite is an open source library that stores and retrieves "
        "huge raster coverages using a SpatiaLite DBMS."
    )
    license = "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later"
    topics = ("rasterlite", "raster", "spatialite")
    homepage = "https://www.gaia-gis.it/fossil/librasterlite"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libgeotiff/[^1.7.1]")
        self.requires("libjpeg-meta/latest")
        self.requires("libpng/[~1.6]")
        self.requires("libspatialite/[^5.0.1]")
        self.requires("libtiff/[>=4.5 <5]")
        self.requires("sqlite3/[>=3.42 <4]")

    def build_requirements(self):
        if not is_msvc(self):
            self.tool_requires("libtool/[^2.4.7]")
            if not self.conf.get("tools.gnu:pkg_config", check_type=str):
                self.tool_requires("pkgconf/[<4]")
            if self.settings_build.os == "Windows":
                self.win_bash = True
                if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                    self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if is_msvc(self):
            tc = NMakeToolchain(self)
            tc.generate()
            deps = NMakeDeps(self)
            deps.generate()
        else:
            env = VirtualBuildEnv(self)
            env.generate()
            if not cross_building(self):
                env = VirtualRunEnv(self)
                env.generate(scope="build")

            tc = AutotoolsToolchain(self)
            tc.configure_args.append("--disable-gcov")
            tc.generate()

            deps = AutotoolsDeps(self)
            deps.generate()
            deps = PkgConfigDeps(self)
            deps.generate()

    def build(self):
        if is_msvc(self):
            target = "rasterlite_i.lib" if self.options.shared else "rasterlite.lib"
            optflags = ["-D_USE_MATH_DEFINES"]
            if self.options.shared:
                optflags.append("-DDLL_EXPORT")
            save(self, os.path.join(self.source_folder, "headers", "config.h"), f"#define VERSION \"{self.version}\"\n")
            with chdir(self, self.source_folder):
                self.run(f"nmake -f makefile.vc {target} OPTFLAGS=\"{' '.join(optflags)}\"")
        else:
            autotools = Autotools(self)
            autotools.autoreconf()
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if is_msvc(self):
            copy(self, "rasterlite.h", src=os.path.join(self.source_folder, "headers"), dst=os.path.join(self.package_folder, "include"))
            copy(self, "*.lib", src=self.source_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.dll", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        else:
            autotools = Autotools(self)
            autotools.install()
            rm(self, "*.la", os.path.join(self.package_folder, "lib"))
            rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
            fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "rasterlite")
        suffix = "_i" if is_msvc(self) and self.options.shared else ""
        self.cpp_info.libs = [f"rasterlite{suffix}"]
