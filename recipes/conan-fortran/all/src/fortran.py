import operator
from typing import NamedTuple

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.scm import Version


_STANDARDS = (77, 90, 95, 2003, 2008, 2018, 2023)
_COMPILERS = ("gfortran", "ifort", "ifx", "flang", "nvfortran")
_MANGLING_OVERRIDES = {
    "lower_no_underscore": ("lower", False, False),
    "lower_underscore": ("lower", True, False),
    "lower_underscore_extra": ("lower", True, True),
    "upper_no_underscore": ("upper", False, False),
    "upper_underscore": ("upper", True, False),
    "upper_underscore_extra": ("upper", True, True),
}


class FortranMangling(NamedTuple):
    case: str
    underscore: bool
    extra_underscore: bool

    @property
    def autoconf(self):
        underscore = "underscore" if self.underscore else "no underscore"
        extra = "extra underscore" if self.extra_underscore else "no extra underscore"
        return f"{self.case} case, {underscore}, {extra}"

    @property
    def value(self):
        for value, mangling in _MANGLING_OVERRIDES.items():
            if mangling == tuple(self):
                return value
        raise ConanException(f"Unsupported Fortran name mangling: {self.autoconf}")


def mangling_from_value(value, source="Fortran name mangling"):
    try:
        return FortranMangling(*_MANGLING_OVERRIDES[value])
    except KeyError:
        values = ", ".join(_MANGLING_OVERRIDES)
        raise ConanInvalidConfiguration(
            f"Invalid {source} value '{value}'. Valid values are: {values}"
        )


def validate_settings(conanfile: ConanFile):
    compiler = conanfile.settings.get_safe("fortran")
    if compiler is None:
        raise ConanInvalidConfiguration("The 'fortran' setting must be defined")
    if str(compiler) not in _COMPILERS:
        raise ConanInvalidConfiguration(f"Unsupported Fortran compiler: {compiler}")
    if conanfile.settings.get_safe("fortran.version") is None:
        raise ConanInvalidConfiguration("The 'fortran.version' setting must be defined")
    if conanfile.settings.get_safe("fortran.runtime") is None:
        raise ConanInvalidConfiguration("The 'fortran.runtime' setting must be defined")
    standard = conanfile.settings.get_safe("fortran.std")
    extensions = conanfile.settings.get_safe("fortran.extensions")
    if (standard is None) != (extensions is None):
        raise ConanInvalidConfiguration(
            "The 'fortran.std' and 'fortran.extensions' settings must either both be defined or both be omitted"
        )
    if str(compiler) in ("ifort", "ifx") \
            and conanfile.settings.get_safe("fortran.runtime_type") is None:
        raise ConanInvalidConfiguration(
            "The 'fortran.runtime_type' setting must be defined for Intel Fortran"
        )


def validate_build(conanfile: ConanFile):
    validate_settings(conanfile)
    if not fortran_executable(conanfile):
        raise ConanInvalidConfiguration(
            "A Fortran compiler is required. Please provide one by setting "
            "tools.build:compiler_executables={'fortran': '...'}."
        )


def fortran_executable(conanfile: ConanFile):
    executables = conanfile.conf.get(
        "tools.build:compiler_executables", default={}, check_type=dict
    )
    return executables.get("fortran")


def configure_meson_toolchain(conanfile: ConanFile, toolchain, compiler_args=None):
    """Configure Meson's Fortran compiler until Conan supports it directly."""
    validate_build(conanfile)
    executable = fortran_executable(conanfile)
    toolchain.binaries["fortran"] = ([executable] + list(compiler_args)
                                      if compiler_args else executable)


def fortran_mangling(conanfile: ConanFile):
    """Return the canonical external symbol convention for the selected toolchain.

    Without a configured Fortran toolchain, use the conventional lowercase
    name with one trailing underscore assumed by C implementations of BLAS and
    LAPACK such as OpenBLAS' NOFORTRAN build.

    Intel Fortran on Windows defaults to uppercase external names without a
    suffix. The supported Unix-like toolchains use their conventional
    GNU-compatible lowercase name with one trailing underscore.
    """
    override = conanfile.conf.get(
        "user.conan-fortran:name_mangling", default=None, check_type=str
    )
    if override is not None:
        return mangling_from_value(override, "user.conan-fortran:name_mangling")

    compiler = conanfile.settings.get_safe("fortran")
    if compiler is None:
        return FortranMangling("lower", True, False)
    validate_settings(conanfile)
    compiler = str(compiler)
    if compiler in ("ifort", "ifx") and conanfile.settings.os == "Windows":
        return FortranMangling("upper", False, False)
    return FortranMangling("lower", True, False)


def requires_runtime(conanfile: ConanFile):
    """Add the separately packaged runtime required by the selected compiler."""
    validate_settings(conanfile)
    if not conanfile.conf.get("user.conan-fortran:require_runtime", default=True, check_type=bool):
        return
    if str(conanfile.settings.fortran) not in ("ifort", "ifx"):
        return

    version = Version(conanfile.settings.fortran.version)
    version_range = f"~{version.major}.{version.minor}" if version.minor is not None else f"^{version.major}"
    shared = str(conanfile.settings.fortran.runtime) == "dynamic"
    conanfile.requires(f"intel-fortran-runtime/[{version_range}]", options={"shared": shared})


def add_runtime_to_cpp_info(conanfile: ConanFile, cpp_info):
    """Add the configured Fortran runtime to a library's consumer interface."""
    if "intel-fortran-runtime" in conanfile.dependencies.host:
        requirement = "intel-fortran-runtime::intel-fortran-runtime"
        # An empty root requires list already means all direct dependencies.
        # Do not turn that implicit aggregate into a partial explicit list.
        if (cpp_info is not conanfile.cpp_info or cpp_info.requires) \
                and requirement not in cpp_info.requires:
            cpp_info.requires.append(requirement)
        return

    shared = conanfile.options.get_safe("shared")
    if shared is None:
        shared = str(conanfile.package_type) == "shared-library"
    if not shared and str(conanfile.settings.fortran) == "gfortran" \
            and "gfortran" not in cpp_info.system_libs:
        cpp_info.system_libs.append("gfortran")


def check_min_fortran_std(conanfile: ConanFile, standard):
    _check_fortran_std(conanfile, standard, operator.lt)


def check_max_fortran_std(conanfile: ConanFile, standard):
    _check_fortran_std(conanfile, standard, operator.gt)


def _check_fortran_std(conanfile, standard, comparator):
    try:
        standard = int(str(standard))
    except (TypeError, ValueError):
        raise ConanException("Fortran standard must be a year or 77, 90, or 95")
    if standard not in _STANDARDS:
        raise ConanException(f"Unknown Fortran standard: {standard}")

    current = conanfile.settings.get_safe("fortran.std")
    if current is None:
        raise ConanInvalidConfiguration("The 'fortran.std' setting must be defined for this configuration")
    current = int(str(current))
    if comparator(current, standard):
        relation = "higher" if comparator == operator.gt else "lower"
        raise ConanInvalidConfiguration(
            f"Current Fortran standard ({current}) is {relation} than the required standard ({standard})"
        )


__all__ = [
    "FortranMangling",
    "add_runtime_to_cpp_info",
    "check_max_fortran_std",
    "check_min_fortran_std",
    "configure_meson_toolchain",
    "fortran_executable",
    "fortran_mangling",
    "mangling_from_value",
    "requires_runtime",
    "validate_build",
    "validate_settings",
]
