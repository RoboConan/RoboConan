"""
Functionality related to fetching and handling Nvidia CUDA package archives.
"""

import json
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, get
from conan.tools.scm import Version

from .utils import packages_following_ctk_minor_version, packages_following_ctk_major_version

_redistrib_info_cache = {}


def get_platform_id(_: ConanFile, settings):
    if settings.arch == "armv8" and settings.os == "Linux" and Version(settings.cuda.version) >= "13.0":
        # CUDA 13 unified aarch64 and sbsa platforms into just sbsa, so assume implicit cuda.platform=sbsa for all armv8
        return "linux-sbsa"
    elif settings.get_safe("cuda.platform") == "sbsa":
        if settings.os != "Linux":
            raise ConanInvalidConfiguration(f"Invalid OS for cuda.platform=sbsa: {settings.os}")
        if settings.arch != "armv8":
            raise ConanInvalidConfiguration(f"Invalid architecture for cuda.platform=sbsa: {settings.arch}")
        return "linux-sbsa"
    return {
        ("Windows", "armv8"): "windows-arm64",
        ("Windows", "x86_64"): "windows-x86_64",
        ("Linux", "x86_64"): "linux-x86_64",
        ("Linux", "armv8"): "linux-aarch64",
        ("Linux", "ppc64le"): "linux-ppc64le",
    }.get((str(settings.os), str(settings.arch)))


def get_redistrib_info(conanfile):
    url = conanfile.conan_data["sources"][conanfile.version]["url"]
    redistrib_info = _redistrib_info_cache.get(url)
    if not redistrib_info:
        with TemporaryDirectory() as td:
            temp_path = Path(td, "conan_cuda_redist.json")
            download(conanfile, **conanfile.conan_data["sources"][conanfile.version], filename=temp_path)
            redistrib_info = json.loads(temp_path.read_text(encoding="utf8"))
        redistrib_info["base_url"] = conanfile.conan_data["sources"][conanfile.version]["url"].rsplit("/", 1)[0] + "/"
        _redistrib_info_cache[url] = redistrib_info
    return redistrib_info


def get_package_info(conanfile: ConanFile, package_name: str, ignore_version=False):
    redistrib_info = get_redistrib_info(conanfile)
    package_info = redistrib_info[package_name]
    package_info["base_url"] = redistrib_info["base_url"]
    if not ignore_version:
        assert package_info["version"] == conanfile.version, f"Version mismatch for {package_name}: {package_info['version']} != {conanfile.version}"
    return package_info


def get_package_versions(conanfile: ConanFile):
    redistrib_info = get_redistrib_info(conanfile)
    versions = {pkg: Version(info["version"]) for pkg, info in redistrib_info.items() if isinstance(info, dict)}
    if "release_product" in redistrib_info and redistrib_info["release_product"] not in versions:
        versions[redistrib_info["release_product"]] = redistrib_info["release_label"]
    return versions


def validate_package(conanfile: ConanFile, package_name: str, ignore_version=False):
    platform_id = get_platform_id(conanfile, conanfile.settings)
    if platform_id is None:
        raise ConanInvalidConfiguration(f"Unsupported platform: {conanfile.settings.os}/{conanfile.settings.arch}")
    package_info = get_package_info(conanfile, package_name, ignore_version)
    if "cuda_variant" in package_info:
        cuda_major = conanfile.settings.cuda.version.value.split(".")[0]
        if cuda_major not in package_info["cuda_variant"]:
            supported = ", ".join(f"v{v}" for v in package_info['cuda_variant'])
            suff = "s" if len(package_info['cuda_variant']) > 1 else ""
            raise ConanInvalidConfiguration(f"{conanfile.ref} only supports CUDA major version{suff} {supported} and"
                                            f" is not compatible with cuda.version={conanfile.settings.cuda.version}")
    if conanfile.name in packages_following_ctk_minor_version or package_name in packages_following_ctk_major_version:
        if Version(conanfile.version).major != Version(str(conanfile.settings.cuda.version)).major:
            raise ConanInvalidConfiguration(
                f"Package version is not compatible with cuda.version={conanfile.settings.cuda.version}"
            )
    if platform_id not in package_info:
        raise ConanInvalidConfiguration(f"Unsupported platform {platform_id} for CUDA package '{package_name}'")
    is_static = conanfile.package_type == "static-library" or conanfile.options.get_safe("shared") is False
    libcxx = conanfile.settings.get_safe("compiler.libcxx")
    safe = ["cudart", "culibos", "nvptxcompiler"]  # these don't have a strong dependency on libstdc++
    if conanfile.settings.os == "Linux" and is_static and libcxx not in [None, "libstdc++11"] and conanfile.name not in safe:
        # Most CUDA libraries expose only a C API, so an ABI mismatch between libstdc++ and libc++ is not likely to be an issue.
        # However, linking against both libstdc++ and libc++ simultaneously in a C++ project is not safe.
        conanfile.output.warning(
            f"CUDA Toolkit libraries are built with libstdc++, but compiler.libcxx={libcxx}. "
            f"Using {conanfile.name} in a C++ project is only safe with libcxx=libstdc++11 or with '-o {conanfile.name}/*:shared=False'."
        )


def _chmod_plus_w(path):
    if os.name == "posix":
        os.chmod(path, os.stat(path).st_mode | stat.S_IWUSR)


def download_package(conanfile: ConanFile, package_name: str, scope="host", destination=None, platform_id=None, ignore_version=False, **kwargs):
    destination = destination or conanfile.source_folder
    if scope == "host":
        settings = conanfile.settings
    elif scope == "build":
        settings = conanfile.settings_build
    elif scope == "target":
        settings = conanfile.settings_target
    else:
        raise ConanInvalidConfiguration(f"Unknown scope: {scope}")
    package_info = get_package_info(conanfile, package_name, ignore_version=ignore_version)
    platform_id = platform_id or get_platform_id(conanfile, settings)
    archive_info = package_info[platform_id]
    if "cuda_variant" in package_info:
        cuda_major = conanfile.settings.cuda.version.value.split(".")[0]
        archive_info = archive_info[f"cuda{cuda_major}"]
    url = package_info["base_url"] + archive_info["relative_path"]
    sha256 = archive_info["sha256"]
    get(conanfile, url, sha256=sha256, strip_root=True, destination=destination, **kwargs)
    # Old CTK archives set a read-only flag on LICENSE for some reason. Fix that.
    license_file = os.path.join(destination, "LICENSE")
    if os.path.exists(license_file):
        _chmod_plus_w(license_file)



def require_shared_deps(conanfile: ConanFile, deps: List[str]):
    """Checks if the given dependencies are shared, and raises a ConanInvalidConfiguration if not.
    This is needed for pre-built shared libraries to find their shared dependencies at runtime.

    :param conanfile: The current recipe object. Always use ``self``.
    :param deps: List of dependency names to check.
    """
    for dep_name in deps:
        if dep_name not in conanfile.dependencies.host:
            continue
        dep = conanfile.dependencies.host[dep_name]
        if not dep.options.get_safe("shared", True):
            if "shared" in conanfile.options:
                raise ConanInvalidConfiguration(f"{conanfile.name} requires -o {dep_name}/*:shared=True when -o {conanfile.name}/*:shared=True")
            else:
                raise ConanInvalidConfiguration(f"{conanfile.name} requires -o {dep_name}/*:shared=True")



__all__ = [
    "get_platform_id",
    "get_redistrib_info",
    "get_package_versions",
    "get_package_info",
    "validate_package",
    "download_package",
    "require_shared_deps",
]
