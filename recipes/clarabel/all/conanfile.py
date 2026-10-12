import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.build import cross_building, check_min_cppstd, check_min_cstd
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps, AutotoolsToolchain

required_conan_version = ">=2.4"


class ClarabelConan(ConanFile):
    name = "clarabel"
    description = "Clarabel: C/C++ interface to the Clarabel Interior-point solver for convex conic optimisation problems."
    license = "Apache-2.0"
    homepage = "https://github.com/oxfordcontrol/Clarabel.cpp"
    topics = ("optimization", "linear-programming", "semidefinite-programming", "optimization-algorithms", "quadratic-programming", "convex-optimization", "interior-point-method", "conic-programs", "conic-optimization")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "serde": [True, False],
        "faer_sparse": [True, False],
        "with_blas": ["none", "accelerate", "netlib", "openblas", "mkl", "r"],
    }
    default_options = {
        "shared": False,
        "serde": True,
        "faer_sparse": False,
        "with_blas": "none",
    }

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("eigen/[>=3.3 <6]", transitive_headers=True)
        if self.options.serde:
            self.requires("openssl/[<5]")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.settings.get_safe("compiler.cstd"):
            check_min_cstd(self, 11)

    def build_requirements(self):
        self.tool_requires("rust/[^1.70.0]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["cpp"], strip_root=True)
        get(self, **self.conan_data["sources"][self.version]["rust"], destination="Clarabel.rs", strip_root=True)
        save(self, "examples/CMakeLists.txt", "")

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
        deps = PkgConfigDeps(self)
        deps.generate()

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
    def _shared_flag(self):
        return "--crate-type=cdylib" if self.options.shared else "--crate-type=staticlib"

    def build(self):
        features = []
        if self.options.serde:
            features.append("clarabel/serde")
        if self.options.faer_sparse:
            features.append("clarabel/faer-sparse")
        if self.options.with_blas != "none":
            features.append(f"clarabel/sdp-{self.options.with_blas}")
        cmd = f"cargo rustc -p clarabel_c {self._build_type_flag} {self._shared_flag} --target-dir {self.build_folder}"
        if features:
            cmd += f" --features {','.join(features)}"
        with chdir(self, os.path.join(self.source_folder, "rust_wrapper")):
            self.run(cmd)
            # self.run(f"cbindgen --config cbindgen.toml --quiet --crate clarabel_c --output {self.build_folder}/headers/clarabel.h --lang c")
            # self.run(f"cbindgen --config cbindgen.toml --quiet --crate clarabel_c --output {self.build_folder}/headers/clarabel.hpp")

    @property
    def _dist_dir(self):
        build_type = "debug" if self.settings.build_type == "Debug" else "release"
        if cross_building(self):
            platform = self.conf.get("user.rust:target_host", check_type=str)
            return Path(self.build_folder, platform, build_type)
        return Path(self.build_folder, build_type)

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        # copy(self, "*", os.path.join(self.build_folder, "headers"), os.path.join(self.package_folder, "include"))
        for path in self._dist_dir.glob("*clarabel_c.*"):
            if path.suffix != ".d":
                dest = Path(self.package_folder, "bin" if path.suffix == ".dll" else "lib")
                dest.mkdir(exist_ok=True)
                shutil.copy2(path, os.path.join(dest, path.name))

    def package_info(self):
        self.cpp_info.set_property("cmake_target_aliases", ["libclarabel_c", "libclarabel_c_static", "libclarabel_c_shared"])
        self.cpp_info.set_property("nosoname", True)
        self.cpp_info.libs = ["clarabel_c"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
