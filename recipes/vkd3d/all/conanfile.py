import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc


class Vkd3dConan(ConanFile):
    name = "vkd3d"
    description = "Libraries and tools for porting Direct3D applications to Vulkan"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.winehq.org/wine/vkd3d"
    topics = ("direct3d", "d3d12", "vulkan", "shader", "dxbc")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_spirv_tools": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_spirv_tools": False,
    }
    implements = ["auto_shared_fpic"]
    languages = "C"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("vulkan-headers/[^1.3.228]", transitive_headers=True)
        self.requires("spirv-headers/[^1.3.228]", libs=False, visible=False)
        self.requires("vulkan-loader/[^1.3.228]", headers=False, libs=False, run=True)
        if self.options.with_spirv_tools:
            self.requires("spirv-tools/[^1.3.228]", options={"shared": True})

    def validate(self):
        if self.settings.os == "Windows" and is_msvc(self):
            raise ConanInvalidConfiguration("vkd3d's Autotools build does not support MSVC")

    def build_requirements(self):
        self.tool_requires("bison/[^3.8.2]")
        self.tool_requires("flex/[^2.6.4]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        for filename in ["configure", "demos/make_objc", "libs/vkd3d-shader/make_spirv"]:
            replace_in_file(self, filename, "use JSON;", "use JSON::PP;")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
            "--disable-demos",
            "--disable-tests",
            "--disable-doxygen-doc",
            "--without-ncurses",
            "--without-opengl",
            "--without-xcb",
            "--with-spirv-tools" if self.options.with_spirv_tools else "--without-spirv-tools",
        ])
        for dependency_name in ["vulkan-headers", "spirv-headers"]:
            for include_dir in self.dependencies[dependency_name].cpp_info.aggregated_components().includedirs:
                tc.extra_cflags.append(f"-I{include_dir}")
        if self.options.with_spirv_tools and self.settings.os in ["Linux", "FreeBSD"]:
            for lib_dir in self.dependencies["spirv-tools"].cpp_info.aggregated_components().libdirs:
                tc.extra_ldflags.append(f"-Wl,-rpath-link,{lib_dir}")
        vulkan_soname = {
            "Macos": "libvulkan.1.dylib",
            "Windows": "vulkan-1.dll",
        }.get(str(self.settings.os), "libvulkan.so.1")
        env = tc.environment()
        env.define("SONAME_LIBVULKAN", vulkan_soname)
        tc.generate(env)

        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        shader = self.cpp_info.components["shader"]
        shader.set_property("pkg_config_name", "libvkd3d-shader")
        shader.includedirs = ["include/vkd3d"]
        shader.libs = ["vkd3d-shader"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            shader.system_libs = ["m", "pthread"]
        if self.options.with_spirv_tools:
            shader.requires.extend([
                "spirv-headers::spirv-headers",
                "spirv-tools::spirv-tools-core",
            ])

        core = self.cpp_info.components["core"]
        core.set_property("pkg_config_name", "libvkd3d")
        core.includedirs = ["include/vkd3d"]
        core.libs = ["vkd3d"]
        core.requires = ["shader", "vulkan-headers::vulkanheaders", "vulkan-loader::vulkan-loader"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            core.system_libs = ["dl", "pthread"]

        utils = self.cpp_info.components["utils"]
        utils.set_property("pkg_config_name", "libvkd3d-utils")
        utils.includedirs = ["include/vkd3d"]
        utils.libs = ["vkd3d-utils"]
        utils.requires = ["core", "shader"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            utils.system_libs = ["pthread"]
