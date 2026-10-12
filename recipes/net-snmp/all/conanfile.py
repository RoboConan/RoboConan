import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, NMakeToolchain, unix_path

required_conan_version = ">=2.4"


class NetSnmpConan(ConanFile):
    name = "net-snmp"
    description = (
        "Simple Network Management Protocol (SNMP) is a widely used protocol "
        "for monitoring the health and welfare of network equipment "
        "(eg. routers), computer equipment and even devices like UPSs."
    )
    license = "BSD-3-Clause"
    homepage = "http://www.net-snmp.org/"
    topics = "snmp"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_agent": [True, False],
        "enable_ipv6": [True, False],
        "install_mibs": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_agent": False,
        "enable_ipv6": True,
        "install_mibs": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if is_msvc(self):
            del self.options.enable_agent
            del self.options.install_mibs

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("openssl/[>=1.1 <4]")
        self.requires("pcre/[^8.45]")
        self.requires("zlib-ng/[^2.0]")
        if self.settings.os == "Linux" and self.options.enable_agent:
            self.requires("libnl/[^3.2]")

    def validate(self):
        if is_msvc(self) and self.options.shared:
            # FIXME: Linker errors against third-party dependencies:
            # snmp_openssl.obj : error LNK2019: unresolved external symbol CRYPTO_free referenced in function _extract_oname
            raise ConanInvalidConfiguration(f"{self.ref} fails when building as shared library, use -o '&:shared=False'. Contributions are welcome!")

    def build_requirements(self):
        if is_msvc(self):
            self.tool_requires("strawberryperl/[^5.32.1.1]")
        else:
            self.tool_requires("gnu-config/[*]")
            self.tool_requires("libtool/[^2.4.7]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings.os != "Windows":
            # libtool requires file executable
            self.tool_requires("libmagic/[^5.45]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    @property
    def _is_debug(self):
        return self.settings.build_type == "Debug"

    def generate(self):
        if is_msvc(self):
            tc = NMakeToolchain(self)
            tc.generate()
            # Workaround for "unresolved external symbol" errors during shared build
            env = VirtualRunEnv(self)
            env.generate(scope="build")
        else:
            if not cross_building(self):
                env = VirtualRunEnv(self)
                env.generate(scope="build")
            tc = AutotoolsToolchain(self)
            yes_no = lambda v: "yes" if v else "no"
            openssl_path = self.dependencies["openssl"].package_folder
            zlib_path = self.dependencies["zlib-ng"].package_folder
            tc.configure_args += [
                f"--with-openssl={openssl_path}",
                f"--with-zlib={zlib_path}",
                f"--enable-debugging={yes_no(self._is_debug)}",
                f"--enable-agent={yes_no(self.options.enable_agent)}",
                f"--enable-ipv6={yes_no(self.options.enable_ipv6)}",
                f"--enable-mibs={yes_no(self.options.install_mibs)}",
                "--with-defaults",
                "--without-rpm",
                "--without-pcre",
                "--disable-applications",
                "--disable-manuals",
                "--disable-scripts",
                "--disable-embedded-perl",
            ]
            if self.settings.os in ["Linux"]:
                tc.extra_ldflags.append("-ldl")
                tc.extra_ldflags.append("-lpthread")
            tc.generate()

            deps = PkgConfigDeps(self)
            deps.generate()

    def _patch_msvc(self):
        ssl_info = self.dependencies["openssl"]
        openssl_root = ssl_info.package_folder.replace("\\", "/")
        search_replace = [
            (r'$default_openssldir . "\\include"', f"'{openssl_root}/include'"),
            (r'$default_openssldir . "\\lib\\VC"', f"'{openssl_root}/lib'"),
            ("$openssl = false", "$openssl = true"),
        ]
        if self._is_debug:
            search_replace.append(("$debug = false", "$debug = true"))
        if self.options.shared:
            search_replace.append(("$link_dynamic = false", "$link_dynamic = true"))
        if self.options.with_ipv6:
            search_replace.append(("$b_ipv6 = false", "$b_ipv6 = true"))
        for search, replace in search_replace:
            replace_in_file(self, "build.pl", search, replace)
        replace_in_file(self, "Configure", '"/runtime', f'"/{msvc_runtime_flag(self)}')
        link_lines = "\n".join(
            f'#    pragma comment(lib, "{lib}.lib")'
            for lib in ssl_info.cpp_info.libs + ssl_info.cpp_info.system_libs
        )
        config = r"net-snmp\net-snmp-config.h.in"
        replace_in_file(self, config, "/* Conan: system_libs */", link_lines)

    def _patch_unix(self):
        for gnu_config in [
            self.conf.get("user.gnu-config:config_guess", check_type=str),
            self.conf.get("user.gnu-config:config_sub", check_type=str),
        ]:
            if gnu_config:
                copy(self, os.path.basename(gnu_config), src=os.path.dirname(gnu_config), dst=self.source_folder)
        configure_path = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_path,
                        "-install_name \\$rpath/",
                        "-install_name @rpath/")
        crypto_libs = self.dependencies["openssl"].cpp_info.system_libs
        if len(crypto_libs) != 0:
            crypto_link_flags = " -l".join(crypto_libs)
            replace_in_file(self, configure_path,
                'LIBCRYPTO="-l${CRYPTO}"',
                'LIBCRYPTO="-l${CRYPTO} -l%s"' % (crypto_link_flags,))
            replace_in_file(self, configure_path,
                            'LIBS="-lcrypto  $LIBS"',
                            f'LIBS="-lcrypto -l{crypto_link_flags} $LIBS"')

    def build(self):
        if is_msvc(self):
            with chdir(self, os.path.join(self.source_folder, "win32")):
                self._patch_msvc()
                self.run("perl build.pl")
                self.run("nmake /nologo libsnmp")
        else:
            self._patch_unix()
            configure_path = os.path.join(self.source_folder, "configure")
            os.chmod(configure_path, os.stat(configure_path).st_mode | stat.S_IEXEC)
            autotools = Autotools(self)
            autotools.autoreconf()
            autotools.configure()
            autotools.make(args=["NOAUTODEPS=1"])

    def _dep_config_var(self, name):
        return f"NETSNMP_CONFIG_{name.upper().replace('-', '_')}"

    @property
    def _package_folders(self):
        dirs = [(self.name, self.package_folder)]
        for _, dep in self.dependencies.host.items():
            dirs.append((dep.ref.name, dep.package_folder))
        return dirs

    def _fix_up_config(self):
        # Replace hardcoded paths with environment variables
        config_path = os.path.join(self.package_folder, "bin", "net-snmp-config")
        replace_in_file(self, config_path, "prefix=/", "prefix=${%s}" % self._dep_config_var(self.name))
        for name, package_folder in self._package_folders:
            replace_in_file(self, config_path,
                            unix_path(self, package_folder),
                            "${%s}" % self._dep_config_var(name),
                            strict=False)

    def package(self):
        copy(self, "COPYING",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        if is_msvc(self):
            cfg = "debug" if self._is_debug else "release"
            copy(self, "netsnmp.lib",
                 dst=os.path.join(self.package_folder, "lib"),
                 src=os.path.join(self.source_folder, rf"win32\lib\{cfg}"))
            copy(self, "include/net-snmp/*.h",
                 dst=self.package_folder,
                 src=self.source_folder)
            for directory in ["", "agent/", "library/"]:
                copy(self, f"net-snmp/{directory}*.h",
                     dst=os.path.join(self.package_folder, "include"),
                     src=os.path.join(self.source_folder, "win32"))
        else:
            autotools = Autotools(self)
            # Only install with -j1 as parallel install will break dependencies. Probably a bug in the dependencies.
            autotools.install(args=["-j1"])
            suffix = ".a" if not self.options.shared else ".dylib*" if is_apple_os(self) else ".so*"
            if self.options.enable_agent:
                # make install fails to install these for some reason
                for lib in ["netsnmpagent", "netsnmpmibs"]:
                    copy(self, f"lib{lib}{suffix}",
                         os.path.join(self.build_folder, "agent", ".libs"),
                         os.path.join(self.package_folder, "lib"))
            rm(self, "README", self.package_folder, recursive=True)
            rm(self, "*.la", self.package_folder, recursive=True)
            rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
            fix_apple_shared_install_name(self)
            self._fix_up_config()

    def package_info(self):
        self.cpp_info.components["netsnmp"].set_property("pkg_config_name", "netsnmp")
        self.cpp_info.components["netsnmp"].libs = ["netsnmp"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["netsnmp"].system_libs = ["rt", "pthread", "m"]
        if is_apple_os(self):
            self.cpp_info.components["netsnmp"].frameworks = ["CoreFoundation", "DiskArbitration", "IOKit"]
        self.cpp_info.components["netsnmp"].requires = ["openssl::openssl", "pcre::pcre", "zlib-ng::zlib-ng"]

        if not is_msvc(self):
            if self.options.enable_agent:
                self.cpp_info.components["netsmp-agent"].set_property("pkg_config_name", "netsnmp-agent")
                self.cpp_info.components["netsmp-agent"].libs = ["netsnmpagent", "netsnmpmibs"]
                self.cpp_info.components["netsmp-agent"].requires = ["netsnmp"]
                if self.settings.os == "Linux":
                    self.cpp_info.components["netsmp-agent"].requires.append("libnl::libnl")

            if self.options.install_mibs:
                self.cpp_info.components["netsnmp"].resdirs = ["share"]

            self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
            for name, package_folder in self._package_folders:
                self.buildenv_info.define_path(self._dep_config_var(name), unix_path(self, package_folder))
