import io
import os
import tarfile

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    def layout(self):
        basic_layout(self)

    def test(self):
        save(self, os.path.join(self.build_folder, "libxyz.a"), "")
        self._utils._fix_libnames(self, self.build_folder)
        assert os.path.exists(os.path.join(self.build_folder, "xyz.lib"))

        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w:gz") as archive:
            contents = b"test"
            member = tarfile.TarInfo("opt/intel/bin/compiler/llvm-test")
            member.size = len(contents)
            archive.addfile(member, io.BytesIO(contents))
        payload = payload.getvalue()
        header = (f"{'data.tar.gz/':<16}{0:<12}{0:<6}{0:<6}{100644:<8}"
                  f"{len(payload):<10}`\n").encode()
        deb_contents = b"!<arch>\n" + header + payload
        deb = os.path.join(self.build_folder, "test.deb")
        with open(deb, "wb") as f:
            f.write(deb_contents)
        self._utils.extract_deb(deb, self.build_folder, "opt/intel", pattern="bin/compiler/llvm-*")
        assert load(self, os.path.join(self.build_folder, "bin", "compiler", "llvm-test")) == "test"

        stream_dir = os.path.join(self.build_folder, "stream")
        self._utils.extract_deb(
            io.BytesIO(deb_contents), stream_dir, "opt/intel", path_filter=lambda path: path.endswith("llvm-test")
        )
        assert load(self, os.path.join(stream_dir, "bin", "compiler", "llvm-test")) == "test"
