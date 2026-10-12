import glob
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class SubunitConan(ConanFile):
    name = "subunit"
    description = "A streaming protocol for test results"
    license = "Apache-2.0 OR BSD-3-Clause"
    homepage = "https://launchpad.net/subunit"
    topics = ("subunit", "streaming", "protocol", "test", "results")
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

    @property
    def _is_clang_cl(self):
        return self.settings.os == "Windows" and self.settings.compiler == "clang"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cppunit/[^1.15.1]", transitive_headers=True)

    def build_requirements(self):
        self.tool_requires("libtool/[^2.4.7]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
            self.tool_requires("automake/[^1.18.1]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        tc = AutotoolsToolchain(self)
        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
        tc.configure_args.append("CHECK_CFLAGS= ")
        tc.configure_args.append("CHECK_LIBS= ")
        cppunit_info = self.dependencies["cppunit"].cpp_info
        tc.configure_args.append(f"CPPUNIT_LIBS='{' '.join(cppunit_info.libs)}'")
        tc.configure_args.append("CPPUNIT_CFLAGS= ")
        # Avoid installing i18n + perl things in arch-dependent folders or in a `local` subfolder
        tc.make_args += [
            f"INSTALLARCHLIB={unix_path(self, os.path.join(self.package_folder, 'lib'))}",
            f"INSTALLSITEARCH={unix_path(self, os.path.join(self.build_folder, 'archlib'))}",
            f"INSTALLVENDORARCH={unix_path(self, os.path.join(self.build_folder, 'archlib'))}",
            f"INSTALLSITEBIN={unix_path(self, os.path.join(self.package_folder, 'bin'))}",
            f"INSTALLSITESCRIPT={unix_path(self, os.path.join(self.package_folder, 'bin'))}",
            f"INSTALLSITEMAN1DIR={unix_path(self, os.path.join(self.build_folder, 'share', 'man', 'man1'))}",
            f"INSTALLSITEMAN3DIR={unix_path(self, os.path.join(self.build_folder, 'share', 'man', 'man3'))}",
        ]
        tc.make_args.append("PYTHON=python")
        tc.generate()

        if is_msvc(self) or self._is_clang_cl:
            # AutotoolsDeps causes ./configure to fail on Windows
            env = Environment()
            env.append("CPPFLAGS", [f"-I{unix_path(self, p)}" for p in cppunit_info.includedirs] + [f"-D{d}" for d in cppunit_info.defines])
            env.vars(self).save_script("conanautotoolsdeps_workaround")
        else:
            deps = AutotoolsDeps(self)
            deps.generate()

        if is_msvc(self):
            env = Environment()
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper"))
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper"))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f'{ar_wrapper} lib')
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")
            env.vars(self).save_script("conanbuild_msvc")

    def build(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.autoreconf()
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install()
        rm(self, "*.la", self.package_folder, recursive=True)
        rm(self, "*.pod", self.package_folder, recursive=True)
        for d in glob.glob(os.path.join(self.package_folder, "lib", "python*")):
            rmdir(self, d)
        for d in glob.glob(os.path.join(self.package_folder, "lib", "*")):
            if os.path.isdir(d):
                rmdir(self, d)
        for d in glob.glob(os.path.join(self.package_folder, "*")):
            if os.path.isdir(d) and os.path.basename(d) not in ["bin", "include", "lib", "licenses"]:
                rmdir(self, d)

    def package_info(self):
        self.cpp_info.components["libsubunit"].set_property("pkg_config_name", "libsubunit")
        self.cpp_info.components["libsubunit"].libs = ["subunit"]

        self.cpp_info.components["libcppunit_subunit"].set_property("pkg_config_name", "libcppunit_subunit")
        self.cpp_info.components["libcppunit_subunit"].libs = ["cppunit_subunit"]
        self.cpp_info.components["libcppunit_subunit"].requires = ["cppunit::cppunit"]
