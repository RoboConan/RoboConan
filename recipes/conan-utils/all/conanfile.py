"""
A collection of helper functions for Conan recipes.

You can use them by adding
  python_requires = "conan-utils/latest"
to the top of your ConanFile class, and then calling the functions like this:
  utils = self.python_requires["conan-utils"].module
  utils.limit_build_jobs(self, gb_mem_per_job=4)
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from conan import ConanFile

from src.deb import extract_deb, open_deb_data_tar, extract_subdir_from_tarfile  # NOQA
from src.limit_jobs import limit_build_jobs, monitor_memory_usage  # NOQA
from src.meson_msvc import fix_msvc_libnames, _fix_libnames  # NOQA
from src.python_venv import PythonVenv, pip_install  # NOQA

required_conan_version = ">=2.1"


class ConanUtilsPackage(ConanFile):
    name = "conan-utils"
    version = "latest"
    description = "Miscellaneous Conan helper for functions"
    license = "MIT"
    package_type = "python-require"
    exports = ["src/*.py"]


def lazy_lt_semver(v1, v2):
    return all(int(p1) < int(p2) for p1, p2 in zip(str(v1).split("."), str(v2).split(".")))
