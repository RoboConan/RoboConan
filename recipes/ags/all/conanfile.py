import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, check_min_vs
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class AGSConan(ConanFile):
    name = "ags"
    description = (
        "The AMD GPU Services (AGS) library provides software developers with the ability to query AMD GPU "
        "software and hardware state information that is not normally available through standard operating "
        "systems or graphics APIs."
    )
    license = "MIT"
    homepage = "https://github.com/GPUOpen-LibrariesAndSDKs/AGS_SDK"
    topics = ("amd", "gpu", "pre-built")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    @property
    def _supported_archs(self):
        return ["x86_64", "x86"]

    def validate(self):
        if not is_msvc(self):
            raise ConanInvalidConfiguration("AGS SDK only supports MSVC and Windows")
        check_min_vs(self, 190)
        if Version(self.version) < "6.1.0" and check_min_vs(self, 193, raise_invalid=False):
            raise ConanInvalidConfiguration(f"Visual Studio 2019 or older is required for v{self.version}")
        if self.settings.arch not in self._supported_archs:
            raise ConanInvalidConfiguration(f"AGS SDK doesn't support arch: {self.settings.arch}")
        check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _vs_ide_year(self):
        compiler_version = str(self.settings.compiler.version)
        return {
            "190": "2015",
            "191": "2017",
            "192": "2019",
        }.get(compiler_version, "2022")

    @property
    def _win_arch(self):
        return {
            "x86_64": "x64",
            "x86": "x86",
        }[str(self.settings.arch)]

    @property
    def _lib_name(self):
        if self.options.shared:
            return f"amd_ags_{self._win_arch}"
        return f"amd_ags_{self._win_arch}_{self._vs_ide_year}_{msvc_runtime_flag(self)}"

    def package(self):
        ags_lib_path = os.path.join(self.source_folder, "ags_lib")
        copy(self, "LICENSE.txt",
             dst=os.path.join(self.package_folder, "licenses"),
             src=ags_lib_path)
        copy(self, "*.h",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(ags_lib_path, "inc"))
        copy(self, f"{self._lib_name}.lib",
             dst=os.path.join(self.package_folder, "lib"),
             src=os.path.join(ags_lib_path, "lib"))
        if self.options.shared:
            copy(self, f"{self._lib_name}.dll",
                 dst=os.path.join(self.package_folder, "bin"),
                 src=os.path.join(ags_lib_path, "lib"))

    def package_info(self):
        self.cpp_info.libs = [self._lib_name]
