import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class CoinHslConan(ConanFile):
    name = "coin-hsl"
    description = "Coin-HSL: a collection of HSL linear solvers for IPOPT"
    license = "DocumentRef-LICENCE:LicenseRef-HSL-2.0"
    homepage = "https://licences.stfc.ac.uk/product/coin-hsl"
    topics = ("optimization", "linear-solver", "linear-algebra", "coin-or", "ma27", "ma28", "ma57", "ma77", "ma86", "ma97", "mc19", "mc68")
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

    @property
    def _fortran_compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return executables.get("fortran")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        self.requires("metis/[^5.1]")
        self.requires("openmp/system")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    @property
    def _archive_dir(self):
        return self.conf.get("user.tools:offline_archives_folder", check_type=str, default=None)

    @property
    def _file_name(self):
        return self.conan_data["sources"][self.version]["filename"]

    @property
    def _archive_path(self):
        return os.path.join(self._archive_dir, self._file_name)

    def validate_build(self):
        if not self._archive_dir:
            raise ConanInvalidConfiguration(f"user.tools:offline_archives_folder config variable must be set"
                                            f" to a location containing a {self._file_name} archive file.")
        if not os.path.isfile(self._archive_path):
            raise ConanInvalidConfiguration(
                f"{self._file_name} not found in {self._archive_dir}. "
                f"Please download it from {self.homepage} (after acquiring a license) and place it there."
            )
        if not self._fortran_compiler:
            raise ConanInvalidConfiguration(
                "A Fortran compiler is required. "
                "Please provide one by setting tools.build:compiler_executables={'fortran': '...'}."
            )

    def source(self):
        unzip(self, self._archive_path, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["modules"] = False  # Don't install Fortran modules
        tc.project_options["libmetis_version"] = str(self.dependencies["metis"].ref.version.major)
        tc.generate()
        meson_ini = "conan_meson_cross.ini" if cross_building(self) else "conan_meson_native.ini"
        replace_in_file(self, meson_ini, "[binaries]", f"[binaries]\nfortran = '{self._fortran_compiler}'")

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENCE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "coinhsl")
        self.cpp_info.libs = ["coinhsl"]
        if not self.options.shared:
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs = ["m", "mvec"]
            if "gfortran" in self._fortran_compiler:
                self.cpp_info.system_libs.append("gfortran")
