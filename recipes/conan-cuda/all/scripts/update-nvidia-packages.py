#!/usr/bin/env python3
import argparse
import concurrent
import re
import textwrap
from hashlib import sha256
from pathlib import Path
from pprint import pprint

import requests
import yaml
from conan.tools.scm import Version
from tqdm.auto import tqdm

script_dir = Path(__file__).parent
recipes_root = script_dir.parent.parent.parent


conanfile_version_ranges = {
    "cublasmp/all": ("0.2", None),
    "cudnn/v8": (None, "9.0"),
    "cudnn/all": ("9.0", None),
    "cudss/all": ("0.3", None),
    "cufile/all": ("1.3", None),
    "cupti/all": ("11.5", None),
    "cuquantum/all": ("25.03.0", None),
    "cusparselt/all": ("0.4", None),
    "cutensor/all": ("1.7", None),
    "nvjpeg2k/all": ("0.7", None),
    "nvpl_lapack/all": ("0.3", None),
    "nvpl_sparse/all": ("0.2", None),
    "nvrtc/all": ("11.5", None),
}
conanfile_policies = {
    "cudnn/v8": "latest",
    "cuda-gdb/all": "latest",
    "cuobjdump/all": "latest",
    "cuxxfilt/all": "latest",
    "nvdisasm/all": "latest",
    "nvprof/all": "latest",
    "nvprune/all": "latest",
}
nv_packages = {
    "cuda-crt": ["cuda_crt", "cuda_nvcc"],
    "cuda-opencl": ["cuda_opencl", "cuda_cudart"],
    "cudnn": ["cudnn"],
    "culibos": ["cuda_culibos", "cuda_cudart"],
    "nvptxcompiler": ["libnvptxcompiler", "cuda_nvcc"],
    "nvvm": ["libnvvm", "cuda_nvcc"],
}

cutensornet_versions = {
    "25.09.0": "2.9.0",
    "25.06.0": "2.8.0",
    "25.03.0": "2.7.0",
}


def find_conanfiles():
    return sorted(f for f in recipes_root.rglob("**/conanfile.py") if not f.parent.name.startswith("test_"))


def get_redist_urls(conandata_path):
    urls = set()
    conandata = yaml.safe_load(conandata_path.read_text(encoding="utf-8"))
    for _, info in conandata["sources"].items():
        urls.add(info["url"].rsplit("/", 1)[0])
    return urls


def find_nvidia_redist_json_packages():
    packages = {}
    pattern = re.compile(r'cuda\.download_package\("(\S+)"')
    for conanfile in find_conanfiles():
        content = conanfile.read_text(encoding="utf-8")
        if "cuda.download_package" not in content:
            continue
        conan_pkg_name = conanfile.parent.parent.name
        nv_pkg_names = nv_packages.get(conan_pkg_name)
        if not nv_pkg_names:
            m = pattern.search(content)
            if not m:
                raise ValueError(f"Could not determine NVIDIA package name in {conanfile}")
            nv_pkg_names = [m.group(1)]
        packages[conan_pkg_name] = {
            "nv_packages": nv_pkg_names,
            "urls": get_redist_urls(conanfile.parent / "conandata.yml"),
        }
    return packages


def _process_base_url(base_url, redist_conan_packages):
    r = requests.get(base_url)
    r.raise_for_status()
    redist_files = re.findall(r"redistrib_[^'>]+\.json", r.text)
    relevant_nv_packages = {}
    for conan_pkg, info in redist_conan_packages.items():
        if base_url in info["urls"]:
            for nv_pkg_name in info["nv_packages"]:
                relevant_nv_packages[nv_pkg_name] = conan_pkg
    return [(f"{base_url}/{redist_file}", relevant_nv_packages) for redist_file in redist_files]


def _fetch_and_process_redist_file(url, relevant_nv_packages, hashes, url_dates):
    r = requests.get(url)
    r.raise_for_status()
    hashes[url] = sha256(r.content).hexdigest()
    redist_info = r.json()
    url_dates[url] = redist_info.get("release_date", None)
    results = {}
    for nv_pkg_name, package_info in redist_info.items():
        if not isinstance(package_info, dict) or "version" not in package_info:
            continue
        version = package_info["version"]
        cuda_versions = package_info.get("cuda_variant")
        if cuda_versions:
            cuda_versions = [Version(v) for v in cuda_versions]
        if nv_pkg_name in relevant_nv_packages:
            results[nv_pkg_name] = (version, cuda_versions, url)
    return results


def find_all_redist_package_versions(redist_conan_packages):
    versions = {}
    hashes = {}
    url_dates = {}
    base_urls = sorted(set().union(*(info["urls"] for info in redist_conan_packages.values())))
    redist_urls = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(_process_base_url, base_url, redist_conan_packages) for base_url in base_urls
        ]
        for future in tqdm(
            concurrent.futures.as_completed(futures), total=len(futures), desc="Processing base URLs"
        ):
            redist_urls.extend(future.result())
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(_fetch_and_process_redist_file, url, relevant, hashes, url_dates)
            for url, relevant in redist_urls
        ]
        for future in tqdm(
            concurrent.futures.as_completed(futures), total=len(futures), desc="Fetching redist files"
        ):
            result = future.result()
            # Iterate over "nv_packages" for each Conan package name to allow earlier names to take precedence
            for conan_pkg, info in redist_conan_packages.items():
                for nv_pkg_name in info["nv_packages"]:
                    if nv_pkg_name in result:
                        version, cuda_versions, url = result[nv_pkg_name]
                        if conan_pkg == "cutensornet":
                            if Version(version) < "25.03.0":
                                continue
                            version = cutensornet_versions.get(version.rsplit(".", 1)[0], version)
                        if conan_pkg not in versions:
                            versions[conan_pkg] = {}
                        if version not in versions[conan_pkg]:
                            versions[conan_pkg][version] = []
                        for cuda_major in cuda_versions or [0]:
                            versions[conan_pkg][version].append((cuda_major, url_dates[url], url))
                        break
    return versions, hashes


def _select_versions(versions_dict, version_range=None, policy="latest_minor"):
    if policy not in ["latest", "latest_major", "latest_minor"]:
        raise ValueError(f"Unknown version policy: {policy}")
    groups = {}
    for ver, info in versions_dict.items():
        ver = Version(ver)
        if version_range:
            if version_range[0] is not None and ver < version_range[0]:
                continue
            if version_range[1] is not None and ver >= version_range[1]:
                continue
        if policy == "latest_minor":
            key = (int(ver.major.value), int(ver.minor.value))
        elif policy == "latest_major":
            key = int(ver.major.value)
        else:
            key = None
        for instance in info:
            cuda_major = instance[0]
            combined_key = (cuda_major, key)
            if combined_key not in groups:
                groups[combined_key] = []
            info_subset = [x[1:] for x in info if x[0] == cuda_major]
            groups[combined_key].append((ver, info_subset))
    selected = {}
    for group in groups.values():
        ver, info = sorted(group)[-1]
        # Select the newest URL if the same version exists in multiple
        url = sorted(info)[-1][-1]
        selected[ver] = url
    return sorted(selected.items(), reverse=True)


def _get_supported_cuda_major_versions(selected, versions_dict):
    cuda_major_versions = {}
    for ver, _ in selected:
        cuda_major_versions[ver] = sorted(set(x[0] for x in versions_dict[str(ver)] if x[0] != 0))
    return cuda_major_versions


def _update_conandata(path, versions, supported_cuda_major_versions, hashes):
    parts = ["sources:"]
    for ver, url in versions:
        cuda_ver_comment = ""
        supported = supported_cuda_major_versions.get(ver)
        if supported:
            cuda_ver_comment = f"  # CUDA {', '.join(map(str, supported))}"
        parts.append(textwrap.indent((
            f'"{ver}":{cuda_ver_comment}\n'
            f'  url: "{url}"\n'
            f'  sha256: "{hashes[url]}"'
        ), "  "))
    content = path.read_text(encoding="utf-8")
    content, n = re.subn(r"sources:(?:\n  .+)+", "\n".join(parts), content)
    assert n > 0, f"{path} failed"
    path.write_text(content, encoding="utf-8")


def _update_config_yml(path, versions):
    parts = ["versions:"]
    for ver, folder in versions:
        parts.append(textwrap.indent(f'"{ver}":\n  folder: {folder}', "  "))
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def update_all_conandata(all_versions, hashes):
    for pkg, versions in tqdm(sorted(all_versions.items()), desc="Updating conandata"):
        pkg_versions = []
        for conanfile in recipes_root.joinpath(pkg).rglob("conanfile.py"):
            if conanfile.parent.name.startswith("test_"):
                continue
            rel_path = str(conanfile.parent.relative_to(recipes_root))
            selected_versions = _select_versions(
                versions,
                conanfile_version_ranges.get(rel_path),
                conanfile_policies.get(rel_path, "latest_minor"),
            )
            supported_cuda_major_versions = _get_supported_cuda_major_versions(selected_versions, versions)
            _update_conandata(conanfile.parent.joinpath("conandata.yml"), selected_versions, supported_cuda_major_versions, hashes)
            pkg_versions += [(ver, conanfile.parent.name) for ver, _ in selected_versions]
        pkg_versions = sorted(set(pkg_versions), reverse=True)
        _update_config_yml(recipes_root / pkg / "config.yml", pkg_versions)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "packages",
        nargs="*",
        help="List of specific packages to update. If not provided, all NVIDIA redist packages will be updated.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    redist_conan_packages = find_nvidia_redist_json_packages()
    if args.packages:
        for pkg in args.packages:
            if pkg not in redist_conan_packages:
                raise ValueError(f"Unknown package: {pkg}")
        redist_conan_packages = {pkg: redist_conan_packages[pkg] for pkg in args.packages}
    all_versions, hashes = find_all_redist_package_versions(redist_conan_packages)
    if args.verbose:
        pprint(all_versions)
    update_all_conandata(all_versions, hashes)


if __name__ == "__main__":
    main()
