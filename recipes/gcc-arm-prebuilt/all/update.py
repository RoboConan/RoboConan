#!/usr/bin/env python3
import re
import urllib.parse
from pathlib import Path

import requests
import yaml
from conan.tools.scm import Version
from tqdm.auto import tqdm

script_dir = Path(__file__).resolve().parent


def load_urls(downloads_url):
    content = requests.get(downloads_url).text
    raw_urls = re.findall(r'href="(.+?/downloads/.+?)"', content)
    urls = []
    for url in raw_urls:
        url = urllib.parse.urljoin(downloads_url, url.split("?")[0])
        url = url.replace("/files/", "/Files/")  # both work, be consistent
        if "src-snapshot" in url:
            continue
        if (url.endswith(".tar.xz") or url.endswith(".zip")) and ("gcc-arm" in url or "gnu-toolchain-" in url):
            version = re.search(r"gnu(?:-a)?/(.+?)/", url)[1]
            triplet = re.search(fr"{version}-(.+?)\.(?:tar\.xz|zip)", url)[1]
            urls.append((version, triplet, url))
    return sorted(urls)


def get_checksum(url):
    # Try ".sha256asc" with SHA256 first, then .asc with MD5
    response = requests.get(f"{url}.sha256asc", timeout=5)
    if not response.ok:
        response = requests.get(f"{url}.asc", timeout=5)
        response.raise_for_status()
    return response.text.split()[0].lower()


def main(major_only=False):
    urls = []
    urls += load_urls("https://developer.arm.com/downloads/-/gnu-a")
    urls += load_urls("https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads")
    urls = sorted(urls, key=lambda x: x[1])
    urls = sorted(urls, key=lambda x: Version(x[0]), reverse=True)
    print(f"Found {len(urls)} URLs")

    sources = {}
    major_versions = {}
    for version, triplet, url in tqdm(urls, desc="Loading checksums"):
        if major_only:
            # keep only the latest major release versions
            major = str(Version(version).major)
            if major in major_versions and major_versions[major] != version:
                continue
            major_versions[major] = version

        if version not in sources:
            sources[version] = {}
        sources[version][triplet] = {"url": url}
        try:
            checksum = get_checksum(url)
            algo = "md5" if len(checksum) == 32 else "sha256"
            sources[version][triplet][algo] = checksum
        except Exception:
            pass
    conandata = {"sources": sources}
    conandata_file = script_dir / "conandata.yml"
    conandata_file.write_text(yaml.safe_dump(conandata, sort_keys=False, default_flow_style=False))

    config = {"versions": {v: {"folder": "all"} for v in conandata["sources"].keys()}}
    config_file = script_dir.parent / "config.yml"
    config_file.write_text(yaml.safe_dump(config, sort_keys=False, default_flow_style=False))


if __name__ == "__main__":
    main()
