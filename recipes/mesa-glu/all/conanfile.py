import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class MesaGluConan(ConanFile):
    name = "mesa-glu"
    description = "Mesa's implementation of the OpenGL utility library"
    license = ("SGI-B-1.1", "SGI-B-2.0", "MIT")
    homepage = "https://www.mesa3d.org/"
    topics = ("gl", "glu", "mesa", "opengl")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    provides = "glu"
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
    def _with_libglvnd(self):
        return self.settings.os in ["FreeBSD", "Linux"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # The glu headers include OpenGL headers.
        if self._with_libglvnd:
            self.requires("libglvnd/1.7.0", transitive_headers=True)

    def validate(self):
        if is_apple_os(self) or self.settings.os == "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on {self.settings.os}")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["gl_provider"] = "glvnd" if self._with_libglvnd else "gl"
        tc.generate()
        tc = PkgConfigDeps(self)
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _extract_license(self):
        glu_header = load(self, os.path.join(self.source_folder, "include", "GL", "glu.h"))
        begin = glu_header.find("/*")
        end = glu_header.find("*/", begin)
        return glu_header[begin:end]

    def package(self):
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), self._extract_license())
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["GLU"]
        self.cpp_info.set_property("pkg_config_name", "glu")
