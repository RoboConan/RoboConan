import os
import re
import tarfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class LibsystemdConan(ConanFile):
    name = "libsystemd"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.freedesktop.org/wiki/Software/systemd/"
    description = "System and Service Manager API library"
    topics = ("systemd", "service", "manager")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "with_selinux": [True, False],
        "with_lz4": [True, False],
        "with_xz": [True, False],
        "with_zstd": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "with_selinux": True,
        "with_lz4": True,
        "with_xz": True,
        "with_zstd": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "7",  # gcc 5 is failing
            "clang": "10"
        }

    def requirements(self):
        self.requires("libcap/[^2.69]")
        self.requires("libmount/2.41")
        self.requires("libxcrypt/4.4.36")
        if self.options.with_selinux:
            self.requires("libselinux/3.6")
        if self.options.with_lz4:
            self.requires("lz4/[^1.9.4]")
        if self.options.with_xz:
            self.requires("xz_utils/[^5.4.5]")
        if self.options.with_zstd:
            self.requires("zstd/[~1.5]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("Only Linux supported")
        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if Version(self.version) >= "255.0" and minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires {str(self.settings.compiler)} >= {minimum_version}."
            )

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("m4/[^1.4.20]")
        self.tool_requires("gperf/3.1")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        # Extract using standard Python tools due to Conan's unzip() not handling backslashes in
        # 'units/system-systemd\x2dcryptsetup.slice', etc. correctly.
        download(self, **self.conan_data["sources"][self.version], filename="sources.tar.gz")
        with tarfile.open("sources.tar.gz", "r:gz") as tar:
            tar.extractall()
        move_folder_contents(self, os.path.join(self.source_folder, f"systemd-stable-{self.version}"), self.source_folder)
        apply_conandata_patches(self)
        meson_build = os.path.join(self.source_folder, "meson.build")
        replace_in_file(self, meson_build, "@CONAN_SRC_REL_PATH@", f"'../{Path(self.source_folder).name}'")

    @property
    def _so_version(self):
        meson_build = os.path.join(self.source_folder, "meson.build")
        with open(meson_build, "r", encoding="utf-8") as build_file:
            for line in build_file:
                match = re.match(r"^libsystemd_version = '(.*)'$", line)
                if match:
                    return match.group(1)
        return ""

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

        def _bool(value):
            return "true" if value else "false"

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "disabled"
        tc.project_options["selinux"] = _bool(self.options.with_selinux)
        tc.project_options["lz4"] = _bool(self.options.with_lz4)
        tc.project_options["xz"] = _bool(self.options.with_xz)
        tc.project_options["zstd"] = _bool(self.options.with_zstd)
        tc.project_options["translations"] = _bool(self.options.i18n)

        if self.options.shared:
            tc.project_options["static-libsystemd"] = "false"
        elif self.options.fPIC:
            tc.project_options["static-libsystemd"] = "pic"
        else:
            tc.project_options["static-libsystemd"] = "no-pic"

        # options unrelated to libsystemd
        unrelated = [
            "fdisk", "seccomp", "pwquality", "apparmor", "polkit", "audit",
            "kmod", "microhttpd", "libcryptsetup", "libcurl", "libidn",
            "libidn2", "qrencode", "openssl", "libfido2", "zlib", "xkbcommon",
            "pcre2", "glib", "dbus", "blkid", "gcrypt", "p11kit", "ima",
            "smack", "bzip2", "gnutls", "idn", "initrd", "binfmt", "vconsole",
            "quotacheck", "tmpfiles", "environment-d", "sysusers", "firstboot",
            "randomseed", "backlight", "rfkill", "xdg-autostart", "logind",
            "hibernate", "machined", "portabled", "userdb", "hostnamed",
            "timedated", "timesyncd", "localed", "networkd", "resolve",
            "coredump", "pstore", "efi", "nss-myhostname", "nss-mymachines",
            "nss-resolve", "nss-systemd", "hwdb", "tpm", "man", "html", "utmp",
            "ldconfig", "adm-group", "wheel-group", "gshadow", "install-tests",
            "link-udev-shared", "link-systemctl-shared", "analyze", "pam",
            "link-networkd-shared", "link-timesyncd-shared", "kernel-install",
            "libiptc", "elfutils", "repart", "homed", "importd", "acl",
            "dns-over-tls", "log-trace"]

        unrelated.append("oomd")
        unrelated.extend(["sysext", "nscd"])
        unrelated.append("link-boot-shared")
        unrelated.append("link-journalctl-shared")
        if Version(self.version) < "254.7":
            unrelated.extend(["gnu-efi", "valgrind"])
        else:
            unrelated.extend(["passwdqc", "bootloader", "link-portabled-shared"])

        for opt in unrelated:
            tc.project_options[opt] = "false"

        if Version(self.version) < "255":
            # 'rootprefix' is unused during libsystemd packaging but systemd > v247
            # build files require 'prefix' to be a subdirectory of 'rootprefix'.
            tc.project_options["rootprefix"] = "/"  # Since, Conan 1.64

        # There are a few places in libsystemd where pkgconfig dependencies are
        # not used in compile time and only used in link time. And because of
        # that it is not enough to use the 'PkgConfigDeps' generator here. It
        # is also required to provide a path to the header files directly to
        # the compiler.
        for dependency in reversed(self.dependencies.host.topological_sort.values()):
            for includedir in dependency.cpp_info.aggregated_components().includedirs:
                tc.c_args.append(f"-I{includedir}")

        # Workaround for 'include/libintl.h:20:10: warning: "BUILDING_LIBINTL" is not defined, evaluates to 0 [-Wundef]'
        tc.extra_cflags.append("-Wno-error=undef")

        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        target = ("systemd:shared_library" if self.options.shared
                  else "systemd:static_library")
        meson.build(target=f"version.h {target}")
        if self.options.i18n:
            meson.build(target="systemd-gmo")

    def package(self):
        copy(self, "LICENSE.LGPL2.1", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", os.path.join(self.source_folder, "src", "systemd"),
             os.path.join(self.package_folder, "include", "systemd"))

        if self.options.shared:
            copy(self, "libsystemd.so", self.build_folder,
                 os.path.join(self.package_folder, "lib"))
            copy(self, f"libsystemd.so.{self._so_version.split('.')}",
                 self.build_folder, os.path.join(self.package_folder, "lib"))
            copy(self, f"libsystemd.so.{self._so_version}",
                 self.build_folder, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libsystemd.a", self.build_folder,
                 os.path.join(self.package_folder, "lib"))

        if self.options.i18n:
            copy(self, "*.mo",
                 os.path.join(self.build_folder, "po"),
                 os.path.join(self.package_folder, "share", "locale"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libsystemd")
        self.cpp_info.set_property("component_version", str(Version(self.version).major))
        self.cpp_info.libs = ["systemd"]
        self.cpp_info.system_libs = ["rt", "pthread", "dl"]
        if self.options.i18n:
            self.cpp_info.resdirs = ["share"]
