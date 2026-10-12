import os

from conan import ConanFile
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class FfNvCodecHeaders(ConanFile):
    name = "ffnvcodec"
    description = "FFmpeg version of headers required to interface with Nvidia's codec APIs"
    license = "MIT"
    homepage = "https://github.com/FFmpeg/nv-codec-headers"
    topics = ("ffmpeg", "video", "nvidia", "headers", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    options = {
        "prefixless_includes": [True, False],
    }
    default_options = {
        # prefixless headers are not officially exported by FFMpeg, but enable them for versatility
        "prefixless_includes": True,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _extract_license(self):
        # Extract the License/s from the header to a file
        tmp = load(self, os.path.join(self.source_folder, "include", "ffnvcodec", "nvEncodeAPI.h"))
        license_contents = tmp[tmp.find("Copyright (c)"): tmp.find(" */", 1)]
        license_contents = license_contents.replace(" * ", "").replace(" *", "")
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), license_contents)

    def package(self):
        self._extract_license()
        copy(self, "*", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "ffnvcodec")
        # https://github.com/FFmpeg/nv-codec-headers/blob/n13.1.15.0/ffnvcodec.pc.in#L6
        if self.version == "13.1.15.0":
            self.cpp_info.set_property("system_package_version", "13.1.15.0.1")
        if self.options.prefixless_includes:
            self.cpp_info.includedirs.append("include/ffnvcodec")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
