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
        "with_dbus": [True, False],
        "with_dnssd": ["avahi", "mdnsresponder"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_dbus": True,
        "with_dnssd": "avahi",
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
        self.requires("pdfio/[^1.5.2]")
        self.requires("zlib-ng/[^2.0]")
        self.requires("libiconv/[^1.17]")
        self.requires("openssl/[>=1.1 <4]")
        if self.options.with_dnssd == "avahi":
            self.requires("avahi/[>=0.8 <1]")
        elif self.options.with_dnssd == "mdnsresponder":
            self.requires("mdnsresponder/878.200.35")
        if self.options.with_dbus:
            self.requires("dbus/[^1.15]")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        if is_msvc(self):
            self.tool_requires("automake/[^1.18.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # pdfio has been unvendored
        replace_in_file(self, os.path.join("tools", "Dependencies"), "../pdfio/pdfio.h", "")
        replace_in_file(self, os.path.join("tools", "Dependencies"), "../pdfio/pdfio-content.h", "")
        # Don't override the datarootdir
        replace_in_file(self, "configure", 'datarootdir="/usr/share"', "")

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--with-tls=openssl",
            "--enable-dbus" if self.options.with_dbus else "--disable-dbus",
        ])
        if self.options.get_safe("with_dnssd"):
            tc.configure_args.append(f"--with-dnssd={self.options.with_dnssd}")
        tc.make_args.append("DIRS=cups")
        tc.generate()

        cpp_info = CppInfo(self)
        for req, dependency in self.dependencies.items():
            if req.ref.name in ["libiconv"]:
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
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "cups3")
        self.cpp_info.libs = ["cups3"]
        self.cpp_info.includedirs.append(os.path.join("include", "libcups3"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["m", "pthread"])
        elif is_apple_os(self):
            self.cpp_info.frameworks = ["CoreFoundation", "CoreServices", "Security", "SystemConfiguration", "CoreGraphics", "ImageIO"]
