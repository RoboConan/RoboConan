import os
import textwrap
from pathlib import Path

from conan import ConanFile
from conan.tools.build import build_jobs, cross_building
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps

required_conan_version = ">=2.1"


class RumocaConan(ConanFile):
    name = "rumoca"
    description = "A Modelica translator with focus on CasADi, Sympy, JAX, and PyCollimator generation."
    license = "Apache-2.0"
    homepage = "https://github.com/CogniPilot/rumoca"
    topics = ("modelica", "rust")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def build_requirements(self):
        self.tool_requires("rust/[>=1.88 <2]")

    def package_id(self):
        del self.info.settings.compiler

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Add a profile for RelWithDebInfo
        save(self, "Cargo.toml", content=textwrap.dedent("""\
            [profile.release-with-debug]
            inherits = "release"
            debug = true

            [profile.release-opt-size]
            inherits = "release"
            opt-level = "s"
        """), append=True)

    def generate(self):
        env = Environment()
        # Ensure the correct linker is used, especially when cross-compiling
        target_upper = self.conf.get("user.rust:target_host", check_type=str).upper().replace("-", "_")
        cc = AutotoolsToolchain(self).vars().get("CC")
        if cc:
            env.define_path(f"CARGO_TARGET_{target_upper}_LINKER", cc)
        # Don't add the Cargo dependencies to a global Cargo cache
        env.define_path("CARGO_HOME", os.path.join(self.build_folder, "cargo"))
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self).save_script("cargo_paths")
        PkgConfigDeps(self).generate()

    @property
    def _build_type_flag(self):
        if self.settings.build_type == "Debug":
            return ""
        elif self.settings.build_type == "RelWithDebInfo":
            return "--profile=release-with-debug"
        elif self.settings.build_type == "MinSizeRel":
            return "--profile=release-opt-size"
        return "--release"

    @property
    def _cargo_profile(self):
        return {
            "Debug": "debug",
            "RelWithDebInfo": "release-with-debug",
            "MinSizeRel": "release-opt-size",
            "Release": "release",
        }[str(self.settings.build_type)]

    @property
    def _features_flag(self):
        features = (
            "scheduled-sim", "scenario-config", "input-keyboard", "transport-udp",
            "transport-zenoh", "viewer-web", "process-control", "native-allocator",
            "fmu-packaging",
        )
        return f"--no-default-features --features {','.join(features)}"

    def build(self):
        jobs = min(build_jobs(self), 8)
        self.run(
            f"cargo rustc -p rumoca --bin rumoca {self._build_type_flag} {self._features_flag} "
            f"--locked --jobs {jobs} "
            f"--target-dir {self.build_folder}",
            cwd=self.source_folder,
        )

    @property
    def _dist_dir(self):
        if cross_building(self):
            platform = self.conf.get("user.rust:target_host", check_type=str)
            return Path(self.build_folder, platform, self._cargo_profile)
        return Path(self.build_folder, self._cargo_profile)

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "THIRD_PARTY_NOTICES.md", os.path.join(self.source_folder, "infra", "licenses"),
             os.path.join(self.package_folder, "licenses"))
        suffix = ".exe" if self.settings.os == "Windows" else ""
        copy(self, f"rumoca{suffix}", self._dist_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
