"""Common Fortran settings helpers for RoboConan recipes.

Use them from a recipe with::

    python_requires = "conan-fortran/latest"
    python_requires_extend = "conan-fortran.Fortran"
"""

import sys
from functools import cached_property, partial
from pathlib import Path

from conan import ConanFile
from conan.tools.scm import Version

sys.path.append(str(Path(__file__).resolve().parent))

from src.fortran import *  # NOQA

required_conan_version = ">=2.1"


class ConanFortranPackage(ConanFile):
    name = "conan-fortran"
    version = "latest"
    description = "Common Fortran settings and ABI helpers for Conan recipes"
    license = "MIT"
    package_type = "python-require"
    exports = ["src/*.py"]


class Interface:
    _methods = {
        "add_runtime_to_cpp_info",
        "check_max_fortran_std",
        "check_min_fortran_std",
        "configure_meson_toolchain",
        "requires_runtime",
        "validate_build",
        "validate_settings",
    }

    def __init__(self, conanfile):
        self._conanfile = conanfile

    def __getattr__(self, item):
        if item in self._methods:
            return partial(globals()[item], self._conanfile)
        raise AttributeError(f"No method named '{item}' exists in the conan-fortran interface")

    @cached_property
    def compiler(self):
        return str(self._conanfile.settings.fortran)

    @cached_property
    def executable(self):
        return fortran_executable(self._conanfile)

    @cached_property
    def version(self):
        return Version(self._conanfile.settings.fortran.version)

    @cached_property
    def std(self):
        value = self._conanfile.settings.get_safe("fortran.std")
        return int(str(value)) if value is not None else None

    @cached_property
    def extensions(self):
        value = self._conanfile.settings.get_safe("fortran.extensions")
        return None if value is None else str(value) == "True"

    @cached_property
    def runtime(self):
        return str(self._conanfile.settings.fortran.runtime)

    @cached_property
    def runtime_type(self):
        value = self._conanfile.settings.get_safe("fortran.runtime_type")
        return str(value) if value is not None else None

    @cached_property
    def mangling(self):
        return fortran_mangling(self._conanfile)

    @cached_property
    def autoconf_mangling(self):
        return self.mangling.autoconf


class Fortran:
    """Mixin used as ``python_requires_extend = "conan-fortran.Fortran"``."""

    @cached_property
    def fortran(self):
        return Interface(self)
