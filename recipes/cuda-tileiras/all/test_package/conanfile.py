import os

from conan import ConanFile
from conan.tools.files import load
from conan.tools.layout import basic_layout
from conan.tools.scm import Version


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type", "cuda"
    exports_sources = "test.tileirbc.hex"

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def test(self):
        # Adapted from NVIDIA/cutile-python's test_write_simple_module vector-add bytecode.
        bytecode = os.path.join(self.build_folder, "test.tileirbc")
        cubin = os.path.join(self.build_folder, "test.cubin")
        with open(bytecode, "wb") as file:
            file.write(bytes.fromhex(load(self, os.path.join(self.source_folder, "test.tileirbc.hex"))))

        if Version(self.tested_reference_str.split("/")[1]) >= "13.4":
            tile_ir = os.path.join(self.build_folder, "test.tileir")
            self.run(f'tileirdisasm "{bytecode}" > "{tile_ir}"', env="conanbuild")
            disassembly = load(self, tile_ir)
            assert "entry @test_kernel" in disassembly
            assert "addf " in disassembly
            assert "store_view_tko" in disassembly

        self.run(f'tileiras --gpu-name sm_100 "{bytecode}" -o "{cubin}"', env="conanbuild")
        with open(cubin, "rb") as file:
            output = file.read()
        assert output.startswith(b"\x7fELF")
        assert len(output) > 1024
