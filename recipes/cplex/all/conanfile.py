import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.cmake import cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import msvc_runtime_flag
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class CplexConan(ConanFile):
    name = "cplex"
    description = "IBM ILOG CPLEX Optimizer: High-performance optimization solver for linear, mixed-integer and quadratic programming"
    license = "DocumentRef-English.txt:LicenseRef-CPLEX-License-Agreement"
    homepage = "https://www.ibm.com/products/ilog-cplex-optimization-studio/cplex-optimizer"
    topics = ("optimization", "linear-programming", "mixed-integer-programming", "quadratic-programming", "solver")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "tools": [True, False],
        "prefixless_includes": [True, False],
    }
    default_options = {
        "tools": False,
        "prefixless_includes": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.package_type = "shared-library"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type
        del self.info.options.prefixless_includes

    @property
    def _file_pattern(self):
        v = Version(self.version)
        prefix = f"cos_installer_preview-{v.major}.{v.minor}.*"
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.settings.arch == "x86_64":
                return f"{prefix}-linux-x86-64.bin"
            elif self.settings.arch == "armv8":
                return f"{prefix}-linux-arm64.bin"
        elif is_apple_os(self):
            if self.settings.arch == "x86_64":
                return f"{prefix}-osx.zip"
            elif "armv8" in str(self.settings.arch):
                return f"{prefix}-osx-arm64.zip"
        elif self.settings.os == "Windows" and self.settings.arch == "x86_64":
            return f"{prefix}-win-x86-64.exe"
        return None

    def validate(self):
        if self._file_pattern is None:
            raise ConanInvalidConfiguration(f"{self.settings.os}/{self.settings.arch} is not supported")
        if self.settings.os == "Windows":
            if self.settings.compiler != "msvc":
                raise ConanInvalidConfiguration("Only MSVC is supported on Windows")
            if self.settings.compiler.runtime != "dynamic":
                raise ConanInvalidConfiguration("Only compiler.runtime=dynamic is supported on Windows")

    def build_requirements(self):
        if self.settings.os == "Windows":
            self.tool_requires("7zip/[*]")

    @property
    def _archive_dir(self):
        return self.conf.get("user.tools:offline_archives_folder", check_type=str, default=None)

    def validate_build(self):
        if not self._archive_dir:
            raise ConanInvalidConfiguration(f"user.tools:offline_archives_folder config variable must be set"
                                            f" to a location containing a file matching {self._file_pattern}.")
        matching = list(Path(self._archive_dir).glob(self._file_pattern))
        if not matching:
            raise ConanInvalidConfiguration(f"No file matching {self._file_pattern} found in {self._archive_dir}.")
        if len(matching) > 1:
            raise ConanInvalidConfiguration(f"Multiple files matching {self._file_pattern} found in {self._archive_dir}.")

    def _source(self):
        path = next(Path(self._archive_dir).glob(self._file_pattern))
        self.output.info(f"Extracting {path}...")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.run(f"sh '{path}' -i silent -DLICENSE_ACCEPTED=TRUE -DUSER_INSTALL_DIR='{self.source_folder}'")
        elif self.settings.os == "Windows":
            self.run(f'7z x "{path}"')
            self.run(r'7z x "InstallerData\Disk1\InstData\Resource1.zip"')
            installer_jar = next(Path(self.build_folder).rglob("CPLEXOptimizationStudio_*.jar"))
            self.run(f'7z x "{installer_jar}" -o"{self.source_folder}" -y')
            rm(self, "*", self.build_folder)
        else:
            # TODO
            raise NotImplementedError

    def build(self):
        self._source()

    @property
    def _shared_suffix(self):
        v = Version(self.version)
        return f"{v.major}{v.minor}{v.patch}"

    def package(self):
        copy(self, "*", os.path.join(self.source_folder, "license"), os.path.join(self.package_folder, "licenses"))
        for subdir in ["opl", "concert", "cplex", "cpoptimizer"]:
            copy(self, "*", os.path.join(self.source_folder, subdir, "include"), os.path.join(self.package_folder, "include"))
        if self.settings.os in ["Linux", "FreeBSD"]:
            for subdir in ["opl", "concert", "cplex", "cpoptimizer"]:
                copy(self, "*.a", os.path.join(self.source_folder, subdir), os.path.join(self.package_folder, "lib"), keep_path=False)
                copy(self, "*", os.path.join(self.source_folder, subdir, "include"), os.path.join(self.package_folder, "include"))
                if self.options.tools:
                    copy(self, "*", os.path.join(self.source_folder, subdir, "bin"), os.path.join(self.package_folder, "bin"), keep_path=False)
        elif self.settings.os == "Windows":
            # Keep the correct MD/MDd libraries only
            if msvc_runtime_flag(self) == "MDd":
                subdirs = list(Path(self.source_folder).rglob("stat_mda"))
            else:
                subdirs = list(Path(self.source_folder).rglob("stat_mdd"))
            for subdir in subdirs:
                rmdir(self, subdir)
            copy(self, "*/concert.lib", os.path.join(self.source_folder, "concert"), os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*/ilocplex.lib", os.path.join(self.source_folder, "cplex"), os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*/cp.lib", os.path.join(self.source_folder, "cpoptimizer"), os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*/iljs.lib", os.path.join(self.source_folder, "opl"), os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*/opl.lib", os.path.join(self.source_folder, "opl"), os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, f"*/cplex{self._shared_suffix}.lib", os.path.join(self.source_folder, "cplex"), os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, f"*/cplex{self._shared_suffix}.dll", os.path.join(self.source_folder, "cplex"), os.path.join(self.package_folder, "bin"), keep_path=False)
            if self.options.tools:
                copy(self, "*/*.exe", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
                copy(self, "*/opl*.dll", self.source_folder, os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        if self.settings.os != "Windows":
            self.cpp_info.components["cplex_"].set_property("cmake_target_aliases", ["cplex"])
            self.cpp_info.components["cplex_"].libs = ["cplex"]
        else:
            self.cpp_info.components["cplex_"].set_property("cmake_target_aliases", [self._shared_suffix, "cplex"])
            self.cpp_info.components["cplex_"].libs = [f"cplex{self._shared_suffix}"]

        self.cpp_info.components["ilocplex"].set_property("cmake_target_aliases", ["ilocplex"])
        self.cpp_info.components["ilocplex"].libs = ["ilocplex"]
        self.cpp_info.components["ilocplex"].requires = ["cplex_"]

        self.cpp_info.components["concert"].set_property("cmake_target_aliases", ["concert"])
        self.cpp_info.components["concert"].libs = ["concert"]

        self.cpp_info.components["cp"].set_property("cmake_target_aliases", ["cp"])
        self.cpp_info.components["cp"].libs = ["cp"]

        self.cpp_info.components["iljs"].set_property("cmake_target_aliases", ["iljs"])
        self.cpp_info.components["iljs"].libs = ["iljs"]

        self.cpp_info.components["opl"].set_property("cmake_target_aliases", ["opl"])
        self.cpp_info.components["opl"].libs = ["opl"]

        if self.options.prefixless_includes:
            self.cpp_info.components["cplex_"].includedirs.append("include/ilcplex")
            self.cpp_info.components["ilocplex"].includedirs.append("include/ilcplex")
            self.cpp_info.components["concert"].includedirs.append("include/ilconcert")
            self.cpp_info.components["cp"].includedirs.append("include/ilcp")
            self.cpp_info.components["iljs"].includedirs.append("include/ilopl")
            self.cpp_info.components["opl"].includedirs.append("include/ilopl")

        if self.settings.os in ["Linux", "FreeBSD"]:
            for _, c in self.cpp_info.components.items():
                c.system_libs = ["m", "pthread", "dl", "rt"]
