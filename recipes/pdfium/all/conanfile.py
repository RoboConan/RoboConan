import os
from pathlib import Path

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.1"


class PdfiumConan(ConanFile):
    name = "pdfium"
    description = "PDF generation and rendering library."
    license = "BSD-3-Clause"
    homepage = "https://opensource.google/projects/pdfium"
    topics = ("generate", "generation", "rendering", "pdf", "document", "print")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("freetype/[^2.13.2]")
        self.requires("icu/[*]")
        self.requires("lcms/[^2.16]")
        self.requires("libjpeg-meta/latest")
        self.requires("openjpeg/[^2.5.0]")
        self.requires("zlib-ng/[^2.0]")

    def validate(self):
        check_min_cppstd(self, 14)

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["pdfium-cmake"],
            destination=os.path.join(self.source_folder, "pdfium-cmake"), strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["pdfium"],
            destination=self.source_folder)
        get(self, **self.conan_data["sources"][self.version]["trace_event"],
            destination=os.path.join(self.source_folder, "base", "trace_event", "common"))
        get(self, **self.conan_data["sources"][self.version]["chromium_build"],
            destination=os.path.join(self.source_folder, "build"))
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PDFIUM_ROOT"] = self.source_folder.replace("\\", "/")
        tc.variables["PDF_LIBJPEG_TURBO"] = "turbojpeg" in self.dependencies["libjpeg-meta"].cpp_info.components
        tc.variables["PDF_ENABLE_XFA"] = False  # TODO: pdfium-cmake needs updating
        tc.variables["PDF_ENABLE_V8"] = False  # TODO: requires v8
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def _patch_sources(self):
        path = Path(self.source_folder, "core", "fxcodec", "fx_codec.cpp")
        path.write_text("#include <cstdint>\n" + path.read_text())

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join("pdfium-cmake", "cmake"))
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["pdfium"]
        if is_apple_os(self):
            self.cpp_info.frameworks.extend(["AppKit", "CoreFoundation", "CoreGraphics"])

        stdcpp = stdcpp_library(self)
        if stdcpp:
            self.cpp_info.system_libs.append(stdcpp)
