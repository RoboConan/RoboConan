import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class IntelFortranRuntimeConan(ConanFile):
    name = "intel-fortran-runtime"
    description = "Intel oneAPI Fortran runtime libraries"
    license = "DocumentRef-license.txt:LicenseRef-Intel-DevTools-EULA"
    homepage = "https://www.intel.com/content/www/us/en/developer/tools/oneapi/fortran-compiler.html"
    topics = ("intel", "oneapi", "fortran", "runtime", "pre-built")
    package_type = "library"
    settings = "os", "arch", "fortran"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    @property
    def _upstream_minor(self):
        return ".".join(str(self.version).split(".")[:2])

    @property
    def _extracted_root(self):
        return os.path.join(self.build_folder, "extracted")

    def package_id(self):
        self.info.settings.rm_safe("fortran.version")
        self.info.settings.rm_safe("fortran.std")
        self.info.settings.rm_safe("fortran.extensions")
        self.info.settings.rm_safe("fortran.runtime")
        if self.info.settings.os != "Windows":
            self.info.settings.rm_safe("fortran.runtime_type")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ["Linux", "Windows"]:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")
        if self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration("Only x86_64 is supported")
        if str(self.settings.fortran) not in ["ifort", "ifx"]:
            raise ConanInvalidConfiguration("The Intel Fortran runtime requires ifort or ifx")
        shared_runtime = self.settings.fortran.runtime == "dynamic"
        if bool(self.options.shared) != shared_runtime:
            raise ConanInvalidConfiguration("The Intel Fortran runtime linkage must match fortran.runtime")

    def build(self):
        sources = self.conan_data["sources"][self.version][str(self.settings.os)]
        if self.settings.os == "Windows":
            installer = os.path.join(self.build_folder, "installer.exe")
            download(self, **sources, filename=installer)
            installer_dir = os.path.join(self.build_folder, "installer")
            unzip(self, installer, destination=installer_dir)
            components = [
                "intel.oneapi.win.compilers-common",
                "intel.oneapi.win.ifort-compiler",
            ]
            if self.options.shared:
                components.append("intel.oneapi.win.compilers-common-runtime")
            for component in components:
                package_dir = next(Path(installer_dir, "packages").glob(f"{component},*"))
                unzip(self, str(package_dir / "cupPayload.cup"), destination=self._extracted_root)
        else:
            packages = [
                "intel-oneapi-compiler-fortran",
                "intel-oneapi-compiler-fortran-common",
                "intel-oneapi-compiler-shared",
            ]
            if self.options.shared:
                packages.extend([
                    "intel-oneapi-compiler-fortran-runtime",
                    "intel-oneapi-compiler-shared-runtime",
                ])
            for name in packages:
                package_file = os.path.join(self.build_folder, f"{name}.deb")
                download(self, **sources[name], filename=package_file)
                self._utils.extract_deb(
                    package_file,
                    self._extracted_root,
                    f"opt/intel/oneapi/compiler/{self._upstream_minor}",
                )

    def package(self):
        if self.settings.os == "Windows":
            root = os.path.join(self._extracted_root, "_installdir", "compiler", self._upstream_minor)
        else:
            root = self._extracted_root

        copy(self, "*.h", os.path.join(root, "opt", "compiler", "include"),
             os.path.join(self.package_folder, "include"),
             excludes=["omp-tools.h", "omp_lib.h"], keep_path=False)
        copy(self, "LICENSE*", os.path.join(root, "share", "doc", "compiler", "licensing", "fortran"),
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "third-party-programs.txt",
             os.path.join(root, "share", "doc", "compiler", "licensing", "fortran"),
             os.path.join(self.package_folder, "licenses"), keep_path=False)

        if self.settings.os == "Windows":
            self._package_windows(root)
        else:
            self._package_linux(root)

    def _package_linux(self, root):
        libdir = os.path.join(root, "lib")
        if self.options.shared:
            for pattern in [
                "libicaf.so*", "libifcore*.so*", "libifport*.so*", "libimf.so*",
                "libintlc.so*", "libirc.so*", "libirng.so*", "libistrconv.so*",
                "libqkmalloc.so*", "libsvml.so*",
            ]:
                copy(self, pattern, libdir, os.path.join(self.package_folder, "lib"))
            for library in ["libipgo.a", "libirc_s.a"]:
                copy(self, library, libdir, os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "*.a", libdir, os.path.join(self.package_folder, "lib"))

    def _package_windows(self, root):
        libdir = os.path.join(root, "lib")
        bindir = os.path.join(root, "bin")
        if self.options.shared:
            for pattern in [
                "ifconsol.lib", "libifcoremd*.lib", "libifportmd.lib", "libircmd.lib",
                "libircmt.lib", "libmmd.lib", "svml_dispmd.lib", "libipgo.lib",
                "ifmodintr.lib",
            ]:
                copy(self, pattern, libdir, os.path.join(self.package_folder, "lib"))
            for pattern in [
                "libifcorem*.dll", "libifportmd.dll", "libircmd.dll", "libmmd.dll",
                "svml_dispmd.dll",
            ]:
                copy(self, pattern, bindir, os.path.join(self.package_folder, "bin"))
        else:
            copy(self, "*.lib", libdir, os.path.join(self.package_folder, "lib"),
                 excludes=["*md.lib", "*mdd.lib", "*dispmd.lib", "*d.lib"])

    def package_info(self):
        if self.settings.os == "Windows":
            libdir = os.path.join(self.package_folder, "lib")
            if self.options.shared:
                debug = self.settings.get_safe("fortran.runtime_type") == "Debug"
                self.cpp_info.libs = [
                    "ifconsol", "libifcoremdd" if debug else "libifcoremd", "libifportmd",
                    "libircmt", "libmmd", "svml_dispmd",
                ]
                self.buildenv_info.prepend("LIB", libdir, separator=";")
                self.buildenv_info.append("FFLAGS", "/libs:dll")
                self.buildenv_info.append("FCFLAGS", "/libs:dll")
            else:
                self.cpp_info.libs = [
                    "ifconsol", "libifcoremt", "libifport", "libircmt", "libmmt", "svml_dispmt",
                ]
                self.buildenv_info.prepend("LIB", libdir, separator=";")
            if self.settings.get_safe("fortran.runtime_type") == "Debug":
                self.buildenv_info.append("FFLAGS", "/dbglibs")
                self.buildenv_info.append("FCFLAGS", "/dbglibs")
        elif self.options.shared:
            self.cpp_info.libs = ["ifport", "ifcoremt", "imf", "svml", "ipgo", "intlc", "irc_s"]
            self.buildenv_info.prepend_path("LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
            self.buildenv_info.append("FFLAGS", "-shared-intel")
            self.buildenv_info.append("FCFLAGS", "-shared-intel")
        else:
            self.cpp_info.libs = ["ifport", "ifcoremt", "imf", "svml", "ipgo", "irc", "irc_s"]
            self.buildenv_info.prepend_path("LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        if self.settings.os != "Windows":
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
