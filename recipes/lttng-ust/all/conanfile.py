import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class LTTngUSTConan(ConanFile):
    name = "lttng-ust"
    description = "The LTTng User Space Tracing (LTTng-UST) library allows any C/C++ application to be instrumented for and traced by LTTng."
    license = "LGPL-2.1-only AND MIT AND GPL-2.0-only AND BSD-3-Clause AND BSD-2-Clause"
    homepage = "https://lttng.org/"
    topics = ("lttng", "tracing", "ust", "userspace")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("userspace-rcu/[>=0.14.2 <1]", transitive_headers=True, transitive_libs=True)
        self.requires("libnuma/[^2.0]")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("Only Linux is supported")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, "Makefile.in", "doc \\", "\\")
        replace_in_file(self, "Makefile.in", "tests \\", "\\")

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-examples",
            "--disable-man-pages",
        ])
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # https://cmake.org/cmake/help/latest/module/FindLTTngUST.html
        self.cpp_info.set_property("cmake_file_name", "LTTngUST")
        self.cpp_info.set_property("cmake_target_name", "LTTng::UST")
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("pkg_config_name", "lttng-ust_do_not_use")

        self.cpp_info.components["lttng-ust_"].set_property("pkg_config_name", "lttng-ust")
        self.cpp_info.components["lttng-ust_"].libs = ["lttng-ust"]
        self.cpp_info.components["lttng-ust_"].requires = ["lttng-ust-common", "lttng-ust-tracepoint", "libnuma::libnuma"]

        self.cpp_info.components["lttng-ust-ctl"].set_property("pkg_config_name", "lttng-ust-ctl")
        self.cpp_info.components["lttng-ust-ctl"].libs = ["lttng-ust-ctl"]
        self.cpp_info.components["lttng-ust-ctl"].requires = ["lttng-ust-common", "libnuma::libnuma", "userspace-rcu::urcu-qsbr"]

        self.cpp_info.components["lttng-ust-common"].set_property("pkg_config_name", "lttng-ust-common")
        self.cpp_info.components["lttng-ust-common"].libs = ["lttng-ust-common"]
        self.cpp_info.components["lttng-ust-common"].requires = ["userspace-rcu::urcu"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["dl"]

        for variant in ["cyg-profile-fast", "cyg-profile", "dl", "fd", "fork", "libc-wrapper", "pthread-wrapper", "tracepoint"]:
            self.cpp_info.components[f"lttng-ust-{variant}"].set_property("pkg_config_name", f"lttng-ust-{variant}")
            self.cpp_info.components[f"lttng-ust-{variant}"].libs = [f"lttng-ust-{variant}"]
            self.cpp_info.components[f"lttng-ust-{variant}"].requires = ["lttng-ust-common" if variant in ["fd", "tracepoint"] else "lttng-ust_"]
