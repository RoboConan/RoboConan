import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.4"


class LibVertoConan(ConanFile):
    name = "libverto"
    description = "An async event loop abstraction library."
    license = "MIT"
    homepage = "https://github.com/latchset/libverto"
    topics = ("async", "eventloop")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "pthread": [True, False],
        "with_glib": [True, False],
        "with_libev": [True, False],
        "with_libevent": [True, False],
        "with_tevent": [True, False],
        "default": ["glib", "libev", "libevent", "tevent"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "pthread": True,
        "with_glib": False,
        "with_libev": False,
        "with_libevent": True,
        "with_tevent": False,
        "default": "libevent",
    }
    languages = ["C"]

    @property
    def _backend_dict(self):
        return {
            "glib": self.options.with_glib,
            "libev": self.options.with_libev,
            "libevent": self.options.with_libevent,
            "tevent": self.options.with_tevent,
        }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.pthread

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_glib:
            self.requires("glib/[^2.70.0]")
        if self.options.with_libevent:
            self.requires("libevent/[^2.1.12]")
        if self.options.with_libev:
            self.requires("libev/[^4.33]")

    def package_id(self):
        del self.info.options.default

    def validate(self):
        if is_msvc(self):
            # uses dlfcn.h, unistd.h, libgen.h
            raise ConanInvalidConfiguration("libverto does not support MSVC")
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration("Shared libraries are not supported on Windows")

        if not self._backend_dict[str(self.options.default)]:
            raise ConanInvalidConfiguration(f"Default backend({self.options.default}) must be available")

        if self.options.with_tevent:
            # FIXME: missing tevent recipe
            raise ConanInvalidConfiguration("tevent is not (yet) available on conan-center")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("libtool/[^2.4.7]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        tc.configure_args.extend([
            f"--with-pthread={yes_no(self.options.get_safe('pthread'))}",
            f"--with-glib={yes_no(self.options.with_glib)}",
            f"--with-libev={yes_no(self.options.with_libev)}",
            f"--with-libevent={yes_no(self.options.with_libevent)}",
            f"--with-tevent={yes_no(self.options.with_tevent)}",
        ])
        tc.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self,"COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.components["verto"].set_property("pkg_config_name", "libverto")
        self.cpp_info.components["verto"].libs = ["verto"]
        if self.settings.os == "Linux":
            self.cpp_info.components["verto"].system_libs.append("dl")
            if self.options.pthread:
                self.cpp_info.components["verto"].system_libs.append("pthread")

        if self.options.with_glib:
            self.cpp_info.components["verto-glib"].set_property("pkg_config_name", "libverto-glib")
            self.cpp_info.components["verto-glib"].libs = ["verto-glib"]
            self.cpp_info.components["verto-glib"].requires = ["verto", "glib::glib"]

        if self.options.with_libev:
            self.cpp_info.components["verto-libev"].set_property("pkg_config_name", "libverto-libev")
            self.cpp_info.components["verto-libev"].libs = ["verto-libev"]
            self.cpp_info.components["verto-libev"].requires = ["verto", "libev::libev"]

        if self.options.with_libevent:
            self.cpp_info.components["verto-libevent"].set_property("pkg_config_name", "libverto-libevent")
            self.cpp_info.components["verto-libevent"].libs = ["verto-libevent"]
            self.cpp_info.components["verto-libevent"].requires = ["verto", "libevent::libevent"]

        if self.options.with_tevent:
            self.cpp_info.components["verto-tevent"].set_property("pkg_config_name", "libverto-tevent")
            self.cpp_info.components["verto-tevent"].libs = ["verto-tevent"]
            self.cpp_info.components["verto-tevent"].requires = ["verto", "tevent::tevent"]
