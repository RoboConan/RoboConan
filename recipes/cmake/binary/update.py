import re
from pathlib import Path

import requests
from conan.tools.scm import Version


BASE_URL = "https://cmake.org/files"
MIN_VERSION = Version("3.15")

# Maps filename patterns to (OS, arch) tuples.
# Order matters: first match wins.
FILE_PATTERNS = [
    (re.compile(r"cmake-[\d.]+-[Ll]inux-aarch64\.tar\.gz$"), "Linux", "armv8"),
    (re.compile(r"cmake-[\d.]+-[Ll]inux-x86_64\.tar\.gz$"), "Linux", "x86_64"),
    (re.compile(r"cmake-[\d.]+-macos(?:10\.10)?-universal\.tar\.gz$"), "Macos", "universal"),
    (re.compile(r"cmake-[\d.]+-windows-arm64\.zip$"), "Windows", "armv8"),
    (re.compile(r"cmake-[\d.]+-windows-x86_64\.zip$"), "Windows", "x86_64"),
    (re.compile(r"cmake-[\d.]+-win64-x64\.zip$"), "Windows", "x86_64"),
]


def get_subdirs(url):
    """Parse an Apache-style directory listing for subdirectory links."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return re.findall(r'href="(v[\d.]+/)"', resp.text)


def get_sha_files(url):
    """Find cmake-*-SHA-256.txt files (excluding rc/alpha versions) in a directory listing."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    # Match only release versions (not rc*, alpha, beta)
    return re.findall(r'href="(cmake-[\d.]+-SHA-256\.txt)"', resp.text)


def parse_version_from_sha_file(filename):
    """Extract version string from cmake-X.Y.Z-SHA-256.txt."""
    m = re.match(r"cmake-([\d.]+)-SHA-256\.txt", filename)
    return m.group(1) if m else None


def parse_sha_file(text):
    """Parse a SHA-256.txt file into {filename: sha256} dict."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            sha256, fname = parts
            result[fname.strip()] = sha256.strip()
    return result


def match_files(sha_dict, version_str):
    """Match SHA file entries to our target OS/arch combinations."""
    matches = {}  # (os, arch) -> (filename, sha256)
    for fname, sha256 in sha_dict.items():
        for pattern, os_name, arch in FILE_PATTERNS:
            if pattern.search(fname):
                matches[(os_name, arch)] = (fname, sha256)
                break
    return matches


def build_url(subdir, filename):
    return f"{BASE_URL}/{subdir}{filename}"


def main():
    print("Fetching directory listing from cmake.org...")
    subdirs = get_subdirs(f"{BASE_URL}/")

    # Filter to v<major>.<minor> dirs with version >= 3.19
    minor_dirs = {}  # "major.minor" -> subdir name (e.g. "v3.31/")
    for subdir in subdirs:
        ver_str = subdir.rstrip("/")[1:]  # strip leading 'v' and trailing '/'
        try:
            v = Version(ver_str)
        except Exception:
            continue
        if v >= MIN_VERSION:
            minor_dirs[ver_str] = subdir

    print(f"Found {len(minor_dirs)} version directories >= {MIN_VERSION}")

    # For each minor version dir, find SHA files and pick latest patch
    all_versions = {}  # version_str -> {(os, arch): (url, sha256)}

    for minor_ver, subdir in sorted(minor_dirs.items(), key=lambda x: Version(x[0]), reverse=True):
        dir_url = f"{BASE_URL}/{subdir}"
        print(f"  Scanning {subdir}...")

        try:
            sha_files = get_sha_files(dir_url)
        except Exception as e:
            print(f"    Error listing {dir_url}: {e}")
            continue

        if not sha_files:
            print(f"    No SHA-256.txt files found")
            continue

        # Find the latest patch version
        best_version = None
        best_file = None
        for sha_file in sha_files:
            ver_str = parse_version_from_sha_file(sha_file)
            if ver_str is None:
                continue
            v = Version(ver_str)
            if best_version is None or v > best_version:
                best_version = v
                best_file = sha_file

        if best_file is None:
            continue

        ver_str = str(best_version)
        print(f"    Latest: {ver_str} ({best_file})")

        # Download and parse the SHA file
        sha_url = f"{dir_url}{best_file}"
        try:
            resp = requests.get(sha_url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"    Error fetching {sha_url}: {e}")
            continue

        sha_dict = parse_sha_file(resp.text)
        matches = match_files(sha_dict, ver_str)

        if not matches:
            print(f"    No matching files found")
            continue

        entry = {}
        for (os_name, arch), (fname, sha256) in matches.items():
            url = build_url(subdir, fname)
            entry[(os_name, arch)] = (url, sha256)

        all_versions[ver_str] = entry
        found = ", ".join(f"{os_name}/{arch}" for os_name, arch in sorted(entry.keys()))
        print(f"    Found: {found}")

    # Generate conandata.yml
    print(f"\nGenerating conandata.yml with {len(all_versions)} versions...")

    lines = ["sources:"]
    os_order = ["Linux", "Macos", "Windows"]
    arch_order = {"Linux": ["armv8", "x86_64"], "Macos": ["universal"], "Windows": ["armv8", "x86_64"]}

    for ver_str in sorted(all_versions.keys(), key=Version, reverse=True):
        entry = all_versions[ver_str]
        lines.append(f'  "{ver_str}":')
        for os_name in os_order:
            arches_with_data = [a for a in arch_order[os_name] if (os_name, a) in entry]
            if not arches_with_data:
                continue
            lines.append(f"    {os_name}:")
            for arch in arches_with_data:
                url, sha256 = entry[(os_name, arch)]
                lines.append(f"      {arch}:")
                lines.append(f'        url: "{url}"')
                lines.append(f'        sha256: "{sha256}"')

    output = "\n".join(lines) + "\n"

    out_path = Path(__file__).parent / "conandata.yml"
    out_path.write_text(output, encoding="utf-8")
    print(f"Written to {out_path}")

    # Also generate config.yml
    config_lines = ["versions:"]
    for ver_str in sorted(all_versions.keys(), key=Version, reverse=True):
        config_lines.append(f'  "{ver_str}":')
        config_lines.append(f'    folder: "binary"')

    config_output = "\n".join(config_lines) + "\n"
    config_path = Path(__file__).parent.parent / "config.yml"
    config_path.write_text(config_output, encoding="utf-8")
    print(f"Written to {config_path}")


if __name__ == "__main__":
    main()
