import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import *
from conan.tools.gnu import GnuToolchain, Autotools
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"

_target_map = {
    "efm32g": "efm32/g",
    "efm32gg": "efm32/gg",
    "efm32hg": "efm32/hg",
    "efm32lg": "efm32/lg",
    "efm32tg": "efm32/tg",
    "efm32wg": "efm32/wg",
    "gd32f1x0": "gd32/f1x0",
    "lm3s": "lm3s",
    "lm4f": "lm4f",
    "lpc13xx": "lpc13xx",
    "lpc17xx": "lpc17xx",
    "lpc43xx_m0": "lpc43xx/m0",
    "lpc43xx_m4": "lpc43xx/m4",
    "msp432e4": "msp432/e4",
    "nrf51": "nrf/51",
    "nrf52": "nrf/52",
    "pac55xx": "pac55xx",
    "sam3a": "sam/3a",
    "sam3n": "sam/3n",
    "sam3s": "sam/3s",
    "sam3u": "sam/3u",
    "sam3x": "sam/3x",
    "sam4l": "sam/4l",
    "samd": "sam/d",
    "stm32f0": "stm32/f0",
    "stm32f1": "stm32/f1",
    "stm32f2": "stm32/f2",
    "stm32f3": "stm32/f3",
    "stm32f4": "stm32/f4",
    "stm32f7": "stm32/f7",
    "stm32g0": "stm32/g0",
    "stm32g4": "stm32/g4",
    "stm32h7": "stm32/h7",
    "stm32l0": "stm32/l0",
    "stm32l1": "stm32/l1",
    "stm32l4": "stm32/l4",
    "swm050": "swm050",
    "vf6xx": "vf6xx",
}


class Libopencm3Conan(ConanFile):
    name = "libopencm3"
    description = "Low-level open-source library for ARM cortex MCUs"
    license = "LGPL-3.0-or-later"
    homepage = "https://libopencm3.org"
    topics = "arm", "cortex-m", "stm32", "embedded", "bare-metal"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "target": list(_target_map.keys()),
    }
    languages = ["C"]

    def validate(self):
        if self.settings.os != "baremetal":
            raise ConanInvalidConfiguration("libopencm3 only supports bare-metal targets")
        if self.settings.compiler != "gcc":
            raise ConanInvalidConfiguration("libopencm3 requires GCC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        target = str(self.options.target)
        tc = GnuToolchain(self)
        if cross_building(self):
            tc_vars = tc.extra_env.vars(self)
            cross_prefix = tc_vars.get("STRIP", "arm-none-eabi-strip").rsplit("strip", 1)[0]
            tc.make_args["PREFIX"] = cross_prefix
        tc.make_args["TARGETS"] = _target_map[target]
        tc.generate()

    def build(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.make(target="lib")

    def package(self):
        copy(self, "COPYING.LGPL3", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.GPL3", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        copy(self, "*.a", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.ld", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        target = str(self.options.target)
        self.cpp_info.libs = [f"opencm3_{target}"]
        self.cpp_info.set_property("pkg_config_name", f"opencm3_{target}")
        self.cpp_info.defines = [target.upper()]
