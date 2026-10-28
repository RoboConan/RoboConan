import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class IntelFortranConan(ConanFile):
    name = "intel-fortran"
    description = "Intel oneAPI Fortran Compiler"
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://www.intel.com/content/www/us/en/developer/tools/oneapi/fortran-compiler.html"
    topics = ("intel", "oneapi", "compiler", "fortran", "pre-built")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "with_sycl": [True, False],
    }
    default_options = {
        "with_sycl": False,
    }

    upload_policy = "skip"
    build_policy = "missing"

    python_requires = "conan-utils/latest"


    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    @property
    def _target_settings(self):
        return self.settings_target or self.settings

    @property
    def _upstream_minor(self):
        return ".".join(str(self.version).split(".")[:2])

    @property
    def _extracted_root(self):
        return os.path.join(self.build_folder, "extracted")

    @property
    def _compiler_root(self):
        executable = "ifx.exe" if self._target_settings.os == "Windows" else "ifx"
        compilers = list(Path(self._extracted_root).glob(f"**/bin/{executable}"))
        if len(compilers) != 1:
            raise ConanException(f"Expected exactly one {executable} in the extracted payload")
        return str(compilers[0].parent.parent)

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")

    def package_id(self):
        self.info.settings.rm_safe("compiler")
        self.info.settings.rm_safe("build_type")
        if self.settings_target:
            self.info.settings_target = self.settings_target.copy()
            self.info.settings_target.rm_safe("compiler")
            self.info.settings_target.rm_safe("build_type")
            self.info.settings_target.rm_safe("fortran")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"Build OS {self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration("Only x86_64 build machines are supported")
        target = self._target_settings
        if target.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{target.os} is not supported")
        if target.arch != "x86_64":
            raise ConanInvalidConfiguration("Only x86_64 targets are supported")
        if target.os == "Linux" and self.settings.os != "Linux":
            raise ConanInvalidConfiguration("The Linux compiler can only run on Linux")
        if target.os == "Windows" and target.compiler != "msvc":
            raise ConanInvalidConfiguration("The Windows compiler requires the MSVC toolchain")

    def build(self):
        sources = self.conan_data["sources"][self.version][str(self._target_settings.os)]
        if self._target_settings.os == "Windows":
            installer = os.path.join(self.build_folder, "installer.exe")
            download(self, **sources, filename=installer)
            installer_dir = os.path.join(self.build_folder, "installer")
            unzip(self, installer, destination=installer_dir)
            for component in [
                "intel.oneapi.win.compilers-common",
                "intel.oneapi.win.ifort-compiler",
            ]:
                package_dir = next(Path(installer_dir, "packages").glob(f"{component},*"))
                unzip(self, str(package_dir / "cupPayload.cup"), destination=self._extracted_root)
            package_dir = next(Path(installer_dir, "packages").glob("intel.oneapi.win.openmp,*"))
            unzip(self, str(package_dir / "cupPayload.cup"), destination=self._extracted_root,
                  pattern="*/bin/compiler/llvm-*.exe")
        else:
            packages = [
                "intel-oneapi-compiler-fortran",
                "intel-oneapi-compiler-fortran-common",
                "intel-oneapi-compiler-shared",
            ]
            if self.options.get_safe("with_sycl"):
                packages.append("intel-oneapi-compiler-shared-common")
            for name in packages:
                package_file = os.path.join(self.build_folder, f"{name}.deb")
                download(self, **sources[name], filename=package_file)
                self._utils.extract_deb(package_file, self._extracted_root, f"opt/intel/oneapi/compiler/{self._upstream_minor}")
            package_file = os.path.join(self.build_folder, "intel-oneapi-openmp.deb")
            download(self, **sources["intel-oneapi-openmp"], filename=package_file)
            self._utils.extract_deb(
                package_file,
                self._extracted_root,
                f"opt/intel/oneapi/compiler/{self._upstream_minor}",
                pattern="bin/compiler/llvm-*",
            )

    def package(self):
        root = self._compiler_root
        license_dirs = list(Path(root, "share", "doc").glob("**/licensing/fortran"))
        if len(license_dirs) != 1:
            raise ConanException("Expected exactly one Fortran compiler licensing directory")

        copy(self, "*", root, self.package_folder)
        copy(self, "LICENSE*", str(license_dirs[0]),
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "third-party-programs.txt", str(license_dirs[0]),
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        rmdir(self, os.path.join(self.package_folder, ".toolkit_linking_tool"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "env"))

        # Runtime libraries are packaged separately by intel-fortran-runtime.
        # Keep the objects which the compiler driver addresses by absolute path.
        rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        rm(self, "*.so*", os.path.join(self.package_folder, "lib"))
        rm(self, "*.lib", os.path.join(self.package_folder, "lib"))
        rm(self, "*.dll", os.path.join(self.package_folder, "bin"))

        if self._target_settings.os == "Windows" and not self.options.with_sycl:
            # Windows folds the Linux compiler-shared-common payload into
            # compilers-common, so remove that payload after extraction.
            for path in [
                "bin/aocl-ioc64.exe",
                "bin/compiler/README.txt",
                "bin/compiler/append-file.exe",
                "bin/compiler/file-table-tform.exe",
                "bin/compiler/ld.lld.exe",
                "bin/compiler/llc.exe",
                "bin/compiler/lld-link.exe",
                "bin/compiler/lld.exe",
                "bin/compiler/llvm-spirv.exe",
                "bin/compiler/modularize.exe",
                "bin/compiler/spirv-to-ir-wrapper.exe",
                "bin/compiler/sycl-post-link.exe",
                "bin/compiler/yaml2obj.exe",
                "bin/icx-cc.exe",
                "bin/icx-cl.exe",
                "bin/icx.cfg",
                "bin/ioc64.exe",
                "bin/sycl-ls.exe",
                "bin/syclbin-dump.exe",
                "opt/compiler/include/omp-tools.h",
                "opt/compiler/include/omp_lib.h",
            ]:
                rm(self, os.path.basename(path), os.path.join(self.package_folder, os.path.dirname(path)))
            rmdir(self, os.path.join(self.package_folder, "lib", "cmake", "IntelSYCL"))

        if os.name == "posix":
            for executable in Path(self.package_folder, "bin").rglob("*.exe"):
                executable.chmod(executable.stat().st_mode | 0o111)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin", "bin/compiler"]

        executable = os.path.join(self.package_folder, "bin", "ifx")
        if self._target_settings.os == "Windows":
            executable += ".exe"
        self.conf_info.update("tools.build:compiler_executables", {"fortran": executable})
        self.runenv_info.define_path("FC", executable)

        if self._target_settings.os == "Linux":
            self.runenv_info.prepend_path("NLSPATH", os.path.join(self.package_folder, "lib/compiler/locale/%l_%t/%N"))
