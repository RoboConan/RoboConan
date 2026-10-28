import contextlib
import os
import shutil
import tarfile
import tempfile
from pathlib import Path


@contextlib.contextmanager
def open_deb_data_tar(deb_stream):
    if deb_stream.read(8) != b"!<arch>\n":
        raise ValueError("Not a valid ar archive (.deb)")
    while True:
        header = deb_stream.read(60)
        if not header or len(header) < 60:
            break
        name = header[:16].decode().strip()
        size = int(header[48:58].decode().strip())
        if name.startswith("data.tar"):
            with tempfile.TemporaryFile() as tmp:
                shutil.copyfileobj(deb_stream, tmp)
                tmp.truncate(size)
                tmp.seek(0)
                with tarfile.open(fileobj=tmp, mode="r:*") as data_tar:
                    yield data_tar
                    return
        deb_stream.seek(size + (size % 2), 1)
    raise ValueError("No data.tar.* found in deb")


def extract_deb(deb_file, output_dir, subdir="", pattern=None, path_filter=None):
    stream = contextlib.nullcontext(deb_file) if hasattr(deb_file, "read") else open(deb_file, "rb")
    with stream as deb_stream:
        with open_deb_data_tar(deb_stream) as data_tar:
            extract_subdir_from_tarfile(data_tar, subdir, output_dir, pattern, path_filter)


def extract_subdir_from_tarfile(tar, subdir, output_dir, pattern=None, path_filter=None):
    subdir = subdir.strip("/")
    members = []
    for member in tar:
        name = member.name.lstrip("./")
        if subdir and name != subdir and not name.startswith(f"{subdir}/"):
            continue
        relative_path = os.path.relpath(name, subdir) if subdir else name
        if pattern and not Path(relative_path).match(pattern):
            continue
        if path_filter and not path_filter(relative_path):
            continue
        if member.issym():
            link_target = os.path.normpath(os.path.join(os.path.dirname(relative_path), member.linkname))
            if link_target == ".." or link_target.startswith(f"..{os.sep}"):
                continue
        member.path = relative_path
        members.append(member)
    if not members:
        raise ValueError(f"No files found under {subdir}")
    os.makedirs(output_dir, exist_ok=True)
    tar.extractall(path=output_dir, members=members)
