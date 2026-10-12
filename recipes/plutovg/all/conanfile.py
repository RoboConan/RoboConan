import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMakeToolchain, CMake
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class PlutoVGConan(ConanFile):
    name = "plutovg"
    description = "Tiny 2D vector graphics library in C"
    license = "MIT",
    topics = ("vector", "graphics")
    homepage = "https://github.com/sammycage/plutovg"
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
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        if Version(self.version) < "0.0.1":
            replace_in_file(self, "CMakeLists.txt",
                            "add_library(plutovg STATIC)",
                            "add_library(plutovg)\n"
                            "install(TARGETS plutovg LIBRARY DESTINATION lib ARCHIVE DESTINATION lib RUNTIME DESTINATION bin)\n")
            save(self, "example/CMakeLists.txt", "")

    def generate(self):
        if Version(self.version) >= "0.0.1":
            tc = MesonToolchain(self)
            tc.project_options["auto_features"] = "enabled"
            tc.project_options["examples"] = "disabled"
            tc.project_options["tests"] = "disabled"
            tc.generate()
        else:
            tc = CMakeToolchain(self)
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
            tc.cache_variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
            tc.generate()

    def build(self):
        if Version(self.version) >= "0.0.1":
            meson = Meson(self)
            meson.configure()
            meson.build()
        else:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if Version(self.version) >= "0.0.1":
            meson = Meson(self)
            meson.install()
        else:
            cmake = CMake(self)
            cmake.install()
            copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include", "plutovg"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "plutovg")
        self.cpp_info.libs = ["plutovg"]
        self.cpp_info.includedirs = ["include", "include/plutovg"]
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["m"]
        if is_msvc(self) and not self.options.shared:
            self.cpp_info.defines.append("PLUTOVG_BUILD_STATIC")

