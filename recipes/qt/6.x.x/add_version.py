#!/usr/bin/env python3
import sys
from hashlib import sha256
from pathlib import Path

import requests
from conan.tools.scm import Version
from tqdm.auto import tqdm

hashes_base_url = "https://download.qt.io/archive/"
# qt.io does not provide Content-Length info, so using a mirror instead.
sizes_base_url = "https://mirror.netcologne.de/qtproject/archive/"

# Modules that are not available as a downloadable archive and which must be fetched from GitHub instead.
git_components = [
    "qt5",  # the superbuild root repository
    "qtcoap",
    "qtmqtt",
    "qtopcua",
]


def recipe_root(version):
    script_dir = Path(__file__).parent
    return script_dir.joinpath("..", "5.x.x").resolve() if version.major == 5 else script_dir


def get_components_list(base_url, version):
    version = Version(version)
    url = f"{base_url}qt/{version.major}.{version.minor}/{version}/submodules/md5sums.txt"
    r = requests.get(url)
    r.raise_for_status()
    components = []
    for l in r.text.splitlines():
        if not l.endswith(".tar.xz"):
            continue
        components.append(l.split()[1].split("-everywhere")[0])
    if version.major >= 6:
        components += git_components
    return sorted(components)


def git_tag(version):
    return f"v{version}-lts-lgpl" if str(version)[0] == "5" else f"v{version}"


def get_url(base_url, version, component):
    version = Version(version)
    if version.major >= 6 and component in git_components:
        return f"https://github.com/qt/{component}/archive/refs/tags/{git_tag(version)}.tar.gz"
    if version.major == 5:
        return f"{base_url}qt/{version.major}.{version.minor}/{version}/submodules/{component}-everywhere-opensource-src-{version}.tar.xz"
    return f"{base_url}qt/{version.major}.{version.minor}/{version}/submodules/{component}-everywhere-src-{version}.tar.xz"


def get_download_size(session, url):
    with session.head(url) as r:
        r.raise_for_status()
        return int(r.headers["Content-Length"])

def get_hash(session, url):
    sha256sum = sha256()
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=100_000):
            sha256sum.update(chunk)
    return sha256sum.hexdigest().lower()

def add_source_hashes(version):
    components = get_components_list(hashes_base_url, version)
    yml_path = recipe_root(version) / "sources" / f"{version}.yml"
    yml_path.parent.mkdir(exist_ok=True)
    with requests.Session() as session:
        with yml_path.open("w") as f:
            f.write("hashes:\n")
            for component in tqdm(components, desc="Fetching hashes"):
                url = get_url(hashes_base_url, version, component)
                if component in git_components:
                    hash = get_hash(session, url)
                else:
                    r = session.get(url + ".sha256")
                    r.raise_for_status()
                    hash = r.text.split()[0].lower()
                file_size = get_download_size(session, get_url(sizes_base_url, version, component))
                f.write(f'  {component + ":": <19} "{hash}"  # {file_size / 1_000_000: 6.1f} MB\n')
                f.flush()
            if version.major >= 6:
                f.write("git_only:\n")
                for component in git_components:
                    f.write(f'  - {component}\n')

def fetch_gitmodules(version):
    conf_path = recipe_root(version).joinpath("qtmodules", f"{version}.conf")
    conf_path.parent.mkdir(exist_ok=True)
    print(f"Adding qtmodules/{version}.conf...")
    url = f"https://raw.githubusercontent.com/qt/qt5/refs/tags/{git_tag(version)}/.gitmodules"
    r = requests.get(url)
    r.raise_for_status()
    conf_path.write_text(r.text)

if __name__ == "__main__":
    version = Version(sys.argv[1])
    fetch_gitmodules(version)
    add_source_hashes(version)
