import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

required_conan_version = ">=2.1"


class DpdkConan(ConanFile):
    name = "dpdk"
    description = "DPDK: a set of libraries and drivers for fast packet processing"
    # see https://github.com/DPDK/dpdk/blob/main/license/README
    license = "BSD-3-Clause"  # kernel modules are GPL, but we don't build them
    homepage = "https://dpdk.org"
    topics = ("networking", "packets", "drivers")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_apps": [True, False],
        "enable_stdatomic": [True, False],
        "with_jansson": [True, False],
        "with_libarchive": [True, False],
        "with_libbpf": [True, False],
        "with_libbsd": [True, False],
        "with_libibverbs": [True, False],
        "with_libpcap": [True, False],
        "with_openssl": [True, False],
        "platform": ["generic", "generic_aarch32", "ANY"]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_apps": False,
        "enable_stdatomic": False,
        "with_jansson": False,
        "with_libarchive": False,
        "with_libbpf": False,
        "with_libbsd": False,  # FIXME: libbsd on Conan is outdated?
        "with_libibverbs": False,
        "with_libpcap": True,
        "with_openssl": True,
        "platform": "generic",
    }

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if not str(self.settings.arch).startswith("arm") or not cross_building(self):
            del self.options.platform
        elif self.settings.arch != "armv8":
            self.platform = "generic_aarch32"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["libnuma"].shared = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libnuma/[^2.0.16]", options={"shared": True})
        self.requires("elfutils/[>=0.189 <1]")
        self.requires("zlib-ng/[^2.0]")
        # self.requires("linux-headers-generic/[^6.5]", transitive_headers=True)
        if self.options.with_jansson:
            # rte_metrics_telemetry.h
            self.requires("jansson/[^2.14]", transitive_headers=True, transitive_libs=True)
        if self.options.with_libarchive:
            self.requires("libarchive/[^3.7.6]")
        if self.options.with_libbpf:
            self.requires("libbpf/1.4.6")
        if self.options.with_libbsd:
            self.requires("libbsd/0.10.0")
        if self.options.with_libibverbs:
            self.requires("rdma-core/[*]")
        if self.options.with_libpcap:
            self.requires("libpcap/[^1.10.4]", options={"enable_dpdk": False})
        if self.options.with_openssl:
            self.requires("openssl/[<5]")
        # missing:
        # - libmusdk
        # - libxdp
        # - netcope-common
        # - libwd
        # - libisal
        # - dlpack
        # - dmlc
        # - tvmdp
        # - flexran

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("DPDK is only supported on Linux")
        check_min_cppstd(self, 11)
        if not self.dependencies["libnuma"].options.shared:
            # dpdk is strict about its exported symbols and fails when it encounters statically linked libnuma symbols
            raise ConanInvalidConfiguration("libnuma must be built with '-o libnuma/*:shared=True'")

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")
        # Requires Python during build

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Disable -march, -mcpu and -mtune flags, which produce non-portable binaries.
        # Also fails when cross-compiling for armv8.
        replace_in_file(self, os.path.join(self.source_folder, "config", "meson.build"),
                        "if not is_ms_compiler", "if false")

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        # No good way to enable only static/shared except patching?
        tc.project_options["tests"] = "false"
        tc.project_options["disable_apps"] = "false" if self.options.build_apps else "true"
        tc.project_options["enable_stdatomic"] = "true" if self.options.enable_stdatomic else "false"
        tc.project_options["ibverbs_link"] = "shared"  # rdma-core is a shared-library package
        tc.project_options["disable_drivers"] = "bus"
        # tc.extra_cflags.append(f"-I{self.dependencies['linux-headers-generic'].cpp_info.includedir}")
        if self.options.get_safe("platform"):
            tc.properties["platform"] = str(self.options.platform)
        tc.generate()

        PkgConfigDeps(self).generate()

        # To install pyelftools
        venv = self._utils.PythonVenv(self)
        venv.generate()

    @property
    def _site_packages_dir(self):
        return os.path.join(self.build_folder, "site-packages")

    def _pip_install(self, packages):
        self.run(f"python3 -m pip install {' '.join(packages)} --no-cache-dir --target={self._site_packages_dir}")

    def build(self):
        self._utils.pip_install(self, ["pyelftools"])
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "*", os.path.join(self.source_folder, "license"), os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"), recursive=True)
        else:
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)
        self._utils.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libdpdk")
        # The project builds almost 200 libraries.
        self.cpp_info.libs = collect_libs(self)
