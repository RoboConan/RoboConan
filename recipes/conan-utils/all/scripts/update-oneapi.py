#!/usr/bin/env python3
import pathlib
import re
from typing import Dict, List

import requests
import yaml
from conan.tools.scm import Version

PACKAGES = {
    "onemkl": [
        "mkl",
        "mkl-static",
        "mkl-devel",
        "mkl-include",
        # SYCL-specific
        "mkl-dpcpp",
        "mkl-devel-dpcpp",
        "onemkl-license",
        "onemkl-sycl-include",
        "onemkl-sycl-blas",
        "onemkl-sycl-lapack",
        "onemkl-sycl-datafitting",
        "onemkl-sycl-dft",
        "onemkl-sycl-rng",
        "onemkl-sycl-sparse",
        "onemkl-sycl-stats",
        "onemkl-sycl-vm",
        "onemkl-sycl-distributed-dft",
        "onemkl-devel-sycl-distributed-dft",
    ],
    "intel-openmp": ["intel-openmp"],
    "intel-opencl": ["intel-opencl-rt"],
    "intel-ur": ["intel-cmplr-lib-ur"],
    "intel-tcmlib": ["tcmlib"],
    "intel-dpcpp-sycl": [
        "intel-sycl-rt",
        "intel-cmplr-lib-rt",
    ],
}

MIN_VERSIONS = {
    "onemkl": "2024",
    "intel-openmp": "2024",
    "intel-opencl": "2024",
    "intel-ur": "2024",
    "intel-dpcpp-sycl": "2025.1",
}

recipes_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent


def list_all_intel_packages():
    r = requests.get("https://pypi.org/user/IntelAutomationEngineering/")
    return sorted(re.findall(r'"/project/(\S+)/"', r.text))


def load_pypi_json(package: str) -> Dict:
    url = f"https://pypi.org/pypi/{package}/json"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def get_versions(package) -> List[str]:
    data = load_pypi_json(package)
    versions = sorted(data.get("releases", {}).keys(), key=lambda v: Version(v))
    return versions


def index_release_files(package: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Build an index of available files for the package:
    return: { version: { filename: { "url": url, "sha256": sha256 } } }
    """
    data = load_pypi_json(package)
    releases = data.get("releases", {})
    out = {}
    for ver, files in releases.items():
        filemap = {}
        for f in files or []:
            # f keys: filename, digests{sha256}, url, etc.
            fn = f["filename"]
            url = f["url"]
            sha256 = f["digests"]["sha256"]
            filemap[fn] = {"url": url, "sha256": sha256}
        out[ver] = filemap
    return out


def build_sources_for_version(version, packages, per_package_filemaps):
    result = {"Linux": {}, "Windows": {}}
    for pkg in packages:
        files = per_package_filemaps[pkg].get(version)
        if files is None:
            continue
        linux_pkgs = [info for file, info in files.items() if "manylinux" in file and "x86_64" in file]
        if linux_pkgs:
            result["Linux"][pkg] = linux_pkgs[0]
        windows_pkgs = [info for file, info in files.items() if "win_amd64" in file]
        if windows_pkgs:
            result["Windows"][pkg] = windows_pkgs[0]
    return result


def write_yaml(conan_package, version: str, data_obj: Dict) -> None:
    out_dir = recipes_root / conan_package / "all" / "sources"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{version}.yml"
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data_obj,
            f,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )
    print(f"Wrote {out_path}")


def select_versions(versions: list[str], min_version: str) -> list[str]:
    grouped = {}
    for v in versions:
        v = Version(v)
        if v < min_version:
            continue
        key = (v.major, v.minor)
        if key not in grouped or v > grouped[key]:
            grouped[key] = v
    selected_versions = [str(v) for v in sorted(grouped.values())]
    return selected_versions


def check_for_new_onemkl_packages(intel_packages):
    onemkl_packages = set(pkg for pkg in intel_packages if "mkl" in pkg)
    missing = onemkl_packages - set(PACKAGES["onemkl"])
    if missing:
        raise Exception(f"Found new oneMKL packages: {sorted(missing)}\n"
                        "Please update the script and the recipes accordingly.")


def main():
    intel_packages = list_all_intel_packages()
    check_for_new_onemkl_packages(intel_packages)

    for conan_package in PACKAGES:
        packages = PACKAGES[conan_package]
        print(f"Fetching versions for {conan_package} ...")
        root_package = packages[0]
        versions = get_versions(root_package)
        min_version = MIN_VERSIONS.get(conan_package, "0")
        selected_versions = select_versions(versions, min_version)

        print(f"Found {len(selected_versions)} versions")

        print("Indexing package release files from PyPI ...")
        per_package_filemaps = {}
        for pkg in packages:
            print(f"  -> {pkg}")
            per_package_filemaps[pkg] = index_release_files(pkg)

        for ver in selected_versions:
            data_obj = build_sources_for_version(ver, packages, per_package_filemaps)
            write_yaml(conan_package, ver, data_obj)

        with recipes_root.joinpath(conan_package, "config.yml").open("w") as f:
            f.write("versions:\n")
            for ver in reversed(selected_versions):
                f.write(f'  "{ver}":\n')
                f.write(f"    folder: all\n")

        with recipes_root.joinpath(conan_package, "all", "conandata.yml").open("w") as f:
            f.write("# Use recipes/conan-utils/all/scripts/update-oneapi.py to add new versions\n")
            f.write("sources:\n")
            for ver in reversed(selected_versions):
                f.write(f'  "{ver}":\n')

    print("Done.")


if __name__ == "__main__":
    main()
