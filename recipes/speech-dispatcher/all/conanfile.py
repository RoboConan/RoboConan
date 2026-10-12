import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools import CppInfo
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv, Environment
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path

required_conan_version = ">=2.4"



class SpeechDispatcherConan(ConanFile):
    name = "speech-dispatcher"
    description = "Common high-level interface to speech synthesis"
    license = "LGPL-2.1-or-later"
    homepage = "https://freebsoft.org/speechd"
    topics = ("speech", "synthesis", "tts", "text-to-speech")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "with_alsa": [True, False],
        "with_pulseaudio": [True, False],
        "with_pipewire": [True, False],
        "with_flite": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "with_alsa": False,
        "with_pulseaudio": False,
        "with_pipewire": False,
        "with_flite": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]")
        self.requires("dotconf/[^1.4.1]")
        self.requires("libsndfile/[^1.2.2]")
        self.requires("libsystemd/[^255]")

        if self.options.with_alsa:
            self.requires("libalsa/[^1.2.10]")
        if self.options.with_pulseaudio:
            self.requires("pulseaudio/[^17.0]")
        if self.options.with_pipewire:
            self.requires("pipewire/[^1.4.2]")
        if self.options.with_flite:
            self.requires("flite/[^2.2]")

        # TODO:
        # - libonnxruntime
        # - rubberband
        # - espeak-ng
        # - libao

    def validate(self):
        if self.settings.os not in ["Linux"]:
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on {self.settings.os}.")

    def build_requirements(self):
        self.tool_requires("libtool/[^2.4.7]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")

        def opt_enable(what, v):
            return "--{}-{}".format("enable" if v else "disable", what)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            opt_enable("python", False),
            opt_enable("espeak", False),
            opt_enable("espeak-ng", False),
            opt_enable("flite", self.options.with_flite),
            opt_enable("ibmtts", False),
            opt_enable("voxin", False),
            opt_enable("ivona", False),
            opt_enable("pico", False),
            opt_enable("baratinoo", False),
            opt_enable("kali", False),
            opt_enable("pulse", self.options.with_pulseaudio),
            opt_enable("libao", False),
            opt_enable("pipewire", self.options.with_pipewire),
            opt_enable("alsa", self.options.with_alsa),
            opt_enable("oss", False),
            opt_enable("nas", False),
            opt_enable("nls", self.options.i18n),
        ])
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        cpp_info = CppInfo(self)
        for dependency in reversed(self.dependencies.host.topological_sort.values()):
            cpp_info.merge(dependency.cpp_info.aggregated_components())
        env = Environment()
        env.append("CPPFLAGS", [f"-I{unix_path(self, p)}" for p in cpp_info.includedirs] + [f"-D{d}" for d in cpp_info.defines])
        env.append("LDFLAGS", [f"-l{lib}" for lib in cpp_info.libs])
        env.append("LDFLAGS", [f"-L{unix_path(self, p)}" for p in cpp_info.libdirs] + cpp_info.sharedlinkflags + cpp_info.exelinkflags)
        env.append("CFLAGS", cpp_info.cflags)
        env.vars(self).save_script("conanautotoolsdeps_workaround")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING.LGPL", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "info"))
        rmdir(self, os.path.join(self.package_folder, "share", "speech-dispatcher"))
        rmdir(self, os.path.join(self.package_folder, "etc"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "speech-dispatcher")
        self.cpp_info.libs = ["speechd"]
        self.cpp_info.includedirs.append(os.path.join("include", "speech-dispatcher"))
        self.cpp_info.bindirs.append(os.path.join("bin", "speech-dispatcher-modules"))
        self.cpp_info.resdirs = ["share"]

        self.cpp_info.set_property("pkg_config_custom_content", (
            "libexecdir=${exec_prefix}/libexec\n"
            "modulebindir=${libexecdir}/speech-dispatcher-modules\n"))
