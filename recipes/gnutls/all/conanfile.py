import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.2"


class GnuTLSConan(ConanFile):
    name = "gnutls"
    description = "GnuTLS is a secure communications library implementing the SSL, TLS and DTLS protocols"
    homepage = "https://www.gnutls.org"
    license = "GPL-3.0-or-later AND LGPL-2.1-or-later"
    topics = ("tls", "ssl", "secure communications")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_cxx": [True, False],
        "enable_openssl_compatibility": [True, False],
        "tools": [True, False],
        "with_zlib": [True, False],
        "with_zstd": [True, False],
        "with_brotli": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_cxx": True,
        "enable_openssl_compatibility": False,
        "tools": True,
        "with_zlib": True,
        "with_zstd": True,
        "with_brotli": True,
    }
    implements = ["auto_shared_fpic"]

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.enable_cxx:
            self.settings.rm_safe("compiler.libcxx")
            self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("nettle/3.9.1")
        self.requires("gmp/[^6.3.0]")
        self.requires("libiconv/[^1.17]")
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_zstd:
            self.requires("zstd/[~1.5]")
        if self.options.with_brotli:
            self.requires("brotli/[^1.1.0]")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration(f"{self.ref} cannot be deployed by Visual Studio.")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        yes_no = lambda v: "yes" if v else "no"
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-tests",
            "--disable-doc",
            "--disable-guile",
            "--disable-libdane",
            "--disable-manpages",
            "--disable-silent-rules",
            "--disable-full-test-suite",
            "--disable-maintainer-mode",
            "--disable-option-checking",
            "--disable-dependency-tracking",
            "--disable-heartbeat-support",
            "--disable-gtk-doc-html",
            "--without-p11-kit",
            "--disable-rpath",
            "--without-idn",
            "--with-included-unistring",
            "--with-included-libtasn1",
            f"--with-libiconv-prefix={self.dependencies['libiconv'].package_folder}",
            f"--enable-shared={yes_no(self.options.shared)}",
            f"--enable-static={yes_no(not self.options.shared)}",
            f"--with-cxx={yes_no(self.options.enable_cxx)}",
            f"--with-zlib={yes_no(self.options.with_zlib)}",
            f"--with-brotli={yes_no(self.options.with_brotli)}",
            f"--with-zstd={yes_no(self.options.with_zstd)}",
            f"--enable-tools={yes_no(self.options.tools)}",
            f"--enable-openssl-compatibility={yes_no(self.options.enable_openssl_compatibility)}",
        ])
        if is_apple_os(self):
            # fix_apple_shared_install_name() may fail without -headerpad_max_install_names
            # (see https://github.com/conan-io/conan-center-index/pull/15946#issuecomment-1464321305)
            tc.extra_ldflags.append("-headerpad_max_install_names")
        env = tc.environment()
        if cross_building(self):
            # INFO: Undefined symbols for architecture Mac arm64 rpl_malloc and rpl_realloc
            env.define("ac_cv_func_malloc_0_nonnull", "yes")
            env.define("ac_cv_func_realloc_0_nonnull", "yes")
        tc.generate(env)
        autodeps = AutotoolsDeps(self)
        autodeps.generate()
        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)
        save(self, os.path.join(self.package_folder, self._module_file_rel_path), textwrap.dedent(f"""\
            set(GNUTLS_FOUND TRUE)
            set(GNUTLS_VERSION {self.version})
        """))

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-variables.cmake")

    def package_info(self):
        self.cpp_info.libs = ["gnutlsxx", "gnutls"] if self.options.enable_cxx else ["gnutls"]
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "GnuTLS")
        self.cpp_info.set_property("cmake_target_name", "GnuTLS::GnuTLS")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["GNUTLS"])
        self.cpp_info.set_property("cmake_build_modules", [self._module_file_rel_path])
        self.cpp_info.set_property("pkg_config_name", "gnutls")

        if is_apple_os(self):
            self.cpp_info.frameworks = ["Security", "CoreFoundation"]
        elif self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread", "m"]
