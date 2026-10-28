import os
import textwrap
from functools import cached_property
from io import StringIO
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.13"


class NumpyConan(ConanFile):
    name = "numpy"
    description = "NumPy is the fundamental package for scientific computing with Python."
    license = "BSD 3-Clause"
    homepage = "https://numpy.org/devdocs/reference/c-api/index.html"
    topics = ("ndarray", "array", "linear algebra", "npymath")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
    }
    default_options = {
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    @cached_property
    def _python_executable(self):
        return self.conf.get("user.cpython:python", default=None, check_type=str)

    @cached_property
    def _executable_version(self):
        stdout = StringIO()
        self.run(f'"{self._python_executable}" --version', stdout, scope="build")
        return stdout.getvalue().strip().split()[1]

    def package_id(self):
        if self._python_executable:
            self.info.python_version = self._executable_version

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("blas/latest")
        if not self._python_executable:
            self.requires("cpython/[^3]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        mangling = self.dependencies["blas"].extension_properties["fortran_name_mangling"]
        if mangling != "lower_underscore":
            raise ConanInvalidConfiguration("NumPy requires BLAS with lower_underscore names")

    def build_requirements(self):
        self.tool_requires("ninja/[^1.10]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if not self._python_executable:
            self.tool_requires("cpython/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["numpy"], strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["meson"], strip_root=True, destination=self._meson_root)
        # Add missing wrapper scripts to the vendored meson
        save(self, self._meson_root / "meson",
             textwrap.dedent("""\
                 #!/usr/bin/env bash
                 meson_dir=$(dirname "$0")
                 export PYTHONDONTWRITEBYTECODE=1
                 exec "$meson_dir/meson.py" "$@"
            """))
        self._chmod_plus_x(self._meson_root.joinpath("meson"))
        save(self, self._meson_root / "meson.cmd",
             textwrap.dedent("""\
                 @echo off
                 set PYTHONDONTWRITEBYTECODE=1
                 CALL python %~dp0/meson.py %*
             """))

    @property
    def _meson_root(self):
        return Path(self.source_folder, "vendored-meson", "meson")

    @staticmethod
    def _chmod_plus_x(name):
        os.chmod(name, os.stat(name).st_mode | 0o111)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["allow-noblas"] = False
        tc.project_options["blas-order"] = ["openblas"]
        tc.project_options["lapack-order"] = ["openblas"]
        tc.generate()

        tc = PkgConfigDeps(self)
        tc.generate()

        venv = self._utils.PythonVenv(self)
        venv.generate()

        env = Environment()
        env.prepend_path("PATH", str(self._meson_root))
        env.vars(self).save_script("meson_root")

    def build(self):
        self._utils.pip_install(self, ["cython"])
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "LICENSE*.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, self._prefix_dir / "lib" / "pkgconfig")

    @cached_property
    def _prefix_dir(self):
        # E.g. <package_folder>/lib/python3.13/site-packages/numpy/_core on Linux
        return next(p.parent.parent.parent for p in Path(self.package_folder).rglob("numpyconfig.h"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "numpy")
        self.cpp_info.includedirs = [str(self._prefix_dir / "include")]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.runenv_info.prepend_path("PYTHONPATH", str(self._prefix_dir.parent.parent))
