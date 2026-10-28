import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.13"


class CoinHslConan(ConanFile):
    name = "coin-hsl"
    description = "Coin-HSL: a collection of HSL linear solvers for IPOPT"
    license = "DocumentRef-LICENCE:LicenseRef-HSL-2.0"
    homepage = "https://licences.stfc.ac.uk/product/coin-hsl"
    topics = ("optimization", "linear-solver", "linear-algebra", "coin-or", "ma27", "ma28", "ma57", "ma77", "ma86", "ma97", "mc19", "mc68")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type", "fortran"
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

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        self.fortran.validate_settings()

    def requirements(self):
        self.requires("lapack/latest")
        self.requires("metis/[^5.1]")
        self.requires("openmp/system")
        self.fortran.requires_runtime()

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
        self.fortran.validate_build()

    def source(self):
        unzip(self, self._archive_path, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["modules"] = False  # Don't install Fortran modules
        tc.project_options["libmetis_version"] = str(self.dependencies["metis"].ref.version.major)
        self.fortran.configure_meson_toolchain(tc)
        tc.generate()

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
        self.fortran.add_runtime_to_cpp_info(self.cpp_info)
