#!/usr/bin/env python3
import gzip
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
    "intel-compiler-runtime": ["intel-cmplr-lib-rt"],
    "intel-tcmlib": ["tcmlib"],
    "intel-dpcpp-sycl": ["intel-sycl-rt"],
    "intel-ipp": [
        "ipp",
        "ipp-devel",
        "ipp-include",
        "ipp-static",
    ],
    "intel-ipp-crypto": [
        "ipp-crypto",
        "ipp-crypto-devel",
        "ipp-crypto-include",
        "ipp-crypto-static",
    ],
    "intelmpi": ["impi-rt", "impi-devel"],
}

APT_PACKAGES = {
    "intel-dpcpp": [
        "intel-oneapi-dpcpp-cpp",
        "intel-oneapi-compiler-dpcpp-cpp-common",
        "intel-oneapi-compiler-dpcpp-cpp-runtime",
        "intel-oneapi-compiler-shared",
        "intel-oneapi-compiler-shared-common",
        "intel-oneapi-compiler-shared-runtime",
        "intel-oneapi-openmp",
        "intel-oneapi-dpcpp-debugger",
        "intel-oneapi-dev-utilities",
    ],
}

APT_MIN_VERSIONS = {
    "intel-dpcpp": "2025.3",
}

MIN_VERSIONS = {
    "onemkl": "2024",
    "intel-openmp": "2024",
    "intel-opencl": "2025.3",
    "intel-ur": "2025.3",
    "intel-compiler-runtime": "2025.3",
    "intel-dpcpp-sycl": "2025.3",
    "intel-ipp": "2026",
    "intel-ipp-crypto": "2026",
    "intelmpi": "2021.15",
    "umf": "1.0",
}

IGNORED_ONEMKL_PACKAGES = {
    # Python bindings and NumPy integrations, not oneMKL binary payloads.
    "mkl-fft",
    "mkl-random",
    "mkl-service",
    "mkl-umath",
}

COMPLETE_PACKAGE_SETS = {
    "intel-ipp": {},
    "intel-ipp-crypto": {
        # Linux does not publish an import-library package.
        "Linux": {"ipp-crypto-devel"},
    },
    "intelmpi": {},
}

recipes_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent


def list_all_intel_packages():
    r = requests.get("https://software.repos.intel.com/python/pypi/", timeout=30)
    r.raise_for_status()
    return sorted(set(re.findall(r'/python/pypi/([^/]+)/', r.text)))


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


def load_apt_index(architecture: str) -> List[Dict[str, str]]:
    url = f"https://apt.repos.intel.com/oneapi/dists/all/main/binary-{architecture}/Packages.gz"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    contents = gzip.decompress(r.content).decode()
    packages = []
    for paragraph in contents.split("\n\n"):
        fields = dict(re.findall(r"^(Package|Version|Filename|SHA256): (.*)$", paragraph, re.MULTILINE))
        if fields:
            packages.append(fields)
    return packages


def apt_product_version(version: str) -> str:
    return version.rsplit("-", 1)[0]


def find_apt_package(index, package: str, version: str, exact=True):
    minor = ".".join(version.split(".")[:2])
    candidates = [
        entry for entry in index
        if entry["Package"] == f"{package}-{minor}"
        and apt_product_version(entry["Version"]).startswith(f"{minor}.")
    ]
    if exact:
        candidates = [entry for entry in candidates if apt_product_version(entry["Version"]) == version]
    if not candidates:
        return None
    return max(candidates, key=lambda entry: Version(apt_product_version(entry["Version"])))


def build_apt_sources(version, packages, index):
    result = {"Linux": {}}
    for package in packages:
        optional = package in ["intel-oneapi-dpcpp-debugger", "intel-oneapi-dev-utilities"]
        entry = find_apt_package(index, package, version, exact=not optional)
        if entry is None:
            if optional:
                continue
            raise Exception(f"No APT package found for {package} {version}")
        result["Linux"][package] = {
            "url": f"https://apt.repos.intel.com/oneapi/{entry['Filename']}",
            "sha256": entry["SHA256"],
        }
    return result


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
    return [str(v) for v in sorted(grouped.values())]


def remove_old_sources(conan_package: str, selected_versions: list[str]) -> None:
    sources_dir = recipes_root / conan_package / "all" / "sources"
    for source in sources_dir.glob("*.yml"):
        if source.stem not in selected_versions:
            source.unlink()


def check_for_new_onemkl_packages(intel_packages):
    onemkl_packages = set(pkg for pkg in intel_packages if "mkl" in pkg)
    missing = onemkl_packages - set(PACKAGES["onemkl"]) - IGNORED_ONEMKL_PACKAGES
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
        print("Indexing package release files from PyPI ...")
        per_package_filemaps = {}
        for pkg in packages:
            print(f"  -> {pkg}")
            per_package_filemaps[pkg] = index_release_files(pkg)

        if conan_package in COMPLETE_PACKAGE_SETS:
            versions = [
                version for version in versions
                if all(
                    set(platform_packages) == set(packages) - COMPLETE_PACKAGE_SETS[conan_package].get(platform, set())
                    for platform, platform_packages in build_sources_for_version(
                        version, packages, per_package_filemaps
                    ).items()
                )
            ]
        min_version = MIN_VERSIONS.get(conan_package, "0")
        selected_versions = select_versions(versions, min_version)
        remove_old_sources(conan_package, selected_versions)

        print(f"Found {len(selected_versions)} versions")

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

    apt_index = load_apt_index("amd64") + load_apt_index("all")
    for conan_package, packages in APT_PACKAGES.items():
        root_package = packages[0]
        root_versions = [
            apt_product_version(entry["Version"])
            for entry in apt_index
            if entry["Package"].startswith(f"{root_package}-")
        ]
        selected_versions = select_versions(root_versions, APT_MIN_VERSIONS[conan_package])
        remove_old_sources(conan_package, selected_versions)
        for version in selected_versions:
            write_yaml(conan_package, version, build_apt_sources(version, packages, apt_index))
        with recipes_root.joinpath(conan_package, "config.yml").open("w") as f:
            f.write("versions:\n")
            for version in reversed(selected_versions):
                f.write(f'  "{version}":\n')
                f.write("    folder: all\n")
        with recipes_root.joinpath(conan_package, "all", "conandata.yml").open("w") as f:
            f.write("# Use recipes/conan-utils/all/scripts/update-oneapi.py to add new versions\n")
            f.write("sources:\n")
            for version in reversed(selected_versions):
                f.write(f'  "{version}":\n')

    print("Done.")


if __name__ == "__main__":
    main()
