import os

from conan import ConanFile
from conan.tools import CppInfo
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.4"


class LibcupsConan(ConanFile):
    name = "libcups"
    description = "CUPS is a standards-based, open source printing system"
    license = "Apache-2.0"
    homepage = "https://openprinting.github.io/cups/"
    topics = ("printing", "cups", "ipp")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "with_dbus": [True, False],
        "with_dnssd": ["avahi", "mdnsresponder"],
        "with_gssapi": [True, False],
        "with_libusb": [True, False],
        "with_systemd": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "with_dbus": True,
        "with_dnssd": "avahi",
        "with_gssapi": False,
        "with_libusb": True,
        "with_systemd": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if is_apple_os(self):
            del self.options.with_dnssd

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        self.requires("libiconv/[^1.17]")
        self.requires("openssl/[>=1.1 <4]")
        if self.options.with_dnssd == "avahi":
            self.requires("avahi/[>=0.8 <1]")
        elif self.options.with_dnssd == "mdnsresponder":
            self.requires("mdnsresponder/878.200.35")
        if self.options.with_dbus:
            self.requires("dbus/[^1.15]")
        if self.options.with_libusb:
            self.requires("libusb/[^1.0.26]")
        if self.options.with_gssapi:
            self.requires("krb5/[^1.21]")
        if self.options.with_systemd:
            self.requires("libsystemd/[^255]")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if is_msvc(self):
            self.tool_requires("automake/[^1.18.1]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "configure", '"/usr', r'"\$(prefix)')

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")

        def opt_enable(what, v):
            return "--{}-{}".format("enable" if v else "disable", what)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            opt_enable("dbus", self.options.with_dbus),
            opt_enable("libusb", self.options.with_libusb),
            opt_enable("gssapi", self.options.with_gssapi),
            opt_enable("tcp-wrappers", False),
            opt_enable("ssl", True),
            opt_enable("avahi", self.options.get_safe("with_dnssd") == "avahi"),
            opt_enable("dnssd", self.options.get_safe("with_dnssd") == "mdnsresponder"),
            opt_enable("systemd", self.options.with_systemd),
        ])
        tc.make_args.append("DIRS=cups")
        tc.make_args.append(f"prefix={unix_path(self, self.package_folder)}")
        tc.generate()

        cpp_info = CppInfo(self)
        for req, dependency in self.dependencies.items():
            if req.ref.name in ["libiconv", "krb5"]:
                cpp_info.merge(dependency.cpp_info.aggregated_components())
        env = Environment()
        env.append("CPPFLAGS", [f"-I{unix_path(self, p)}" for p in cpp_info.includedirs] + [f"-D{d}" for d in cpp_info.defines])
        env.append("LDFLAGS", [f"-L{unix_path(self, p)}" for p in cpp_info.libdirs] + cpp_info.sharedlinkflags + cpp_info.exelinkflags)
        env.append("LDFLAGS", [f"-l{l}" for l in cpp_info.libs])
        env.append("CFLAGS", cpp_info.cflags)
        env.vars(self).save_script("conan_custom_autotoolsdeps")

        deps = PkgConfigDeps(self)
        deps.generate()

        if is_msvc(self):
            env = Environment()
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f"{ar_wrapper} lib")
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")
            env.vars(self).save_script("conanbuild_msvc")

    def build(self):
        autotools = Autotools(self)
        with chdir(self, self.source_folder):
            autotools.configure()
            autotools.make()
        if self.options.i18n:
            with chdir(self, os.path.join(self.source_folder, "locale")):
                autotools.make()

    def package(self):
        copy(self, "LICENSE.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        with chdir(self, self.source_folder):
            autotools.install()
        if self.options.i18n:
            with chdir(self, os.path.join(self.source_folder, "locale")):
                autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rm(self, "cups-config", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "cups")
        self.cpp_info.libs = ["cups"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "pthread"])
        elif is_apple_os(self):
            self.cpp_info.frameworks = ["CoreFoundation", "CoreServices", "Security", "SystemConfiguration", "CoreGraphics", "ImageIO"]
