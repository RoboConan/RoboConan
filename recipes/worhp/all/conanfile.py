import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import *

required_conan_version = ">=2.1"


class WorhpConan(ConanFile):
    name = "worhp"
    description = "WORHP: Large-scale Sparse Nonlinear Optimisation"
    license = "LicenseRef-WORHP-proprietary"
    homepage = "https://worhp.de/"
    topics = ("optimization", "nonlinear-optimization", "quadratic-programming")
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "tools": [True, False],
        "worhpmonitor": [True, False],
    }
    default_options = {
        "tools": False,
        "worhpmonitor": False,
    }

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    def config_options(self):
        if self.settings.os != "Windows" or self.settings.arch != "x86_64":
            del self.options.worhpmonitor

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.requires("openblas/[*]", headers=False, options={"shared": True})
            self.requires("superlu/[^6]", headers=False, options={"shared": True})
            self.requires("zlib-ng/[^2]", headers=False, options={"shared": True})

    def validate(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            if self.settings.arch != "x86_64":
                raise ConanInvalidConfiguration("Only x86_64 is supported on Linux")
        elif self.settings.os == "Windows":
            if self.settings.arch not in ["x86_64", "armv8"]:
                raise ConanInvalidConfiguration("Only x86_64 is supported on Windows")
        else:
            raise ConanInvalidConfiguration(f"{self.settings.os} is not supported")

    @property
    def _download_info(self):
        os_ = "Windows" if self.settings.os == "Windows" else "Linux"
        return self.conan_data["sources"][self.version][os_][str(self.settings.arch)]

    @property
    def _archive_dir(self):
        return self.conf.get("user.tools:offline_archives_folder", check_type=str, default=None)

    @property
    def _file_name(self):
        return self._download_info["url"].rsplit("/", 1)[-1]

    @property
    def _archive_path(self):
        return os.path.join(self._archive_dir, self._file_name)

    def validate_build(self):
        if not self._archive_dir:
            raise ConanInvalidConfiguration(f"user.tools:offline_archives_folder config variable must be set"
                                            f" to a location containing a {self._file_name} archive file.")
        if not os.path.isfile(self._archive_path):
            raise ConanInvalidConfiguration(
                f"{self._file_name} not found in {self._archive_dir}. "
                f"Please download it from {self._download_info['url']} and place it there."
            )
        if self.options.get_safe("worhpmonitor"):
            if not os.path.isfile(os.path.join(self._archive_dir, "libworhpmonitor.dll")):
                raise ConanInvalidConfiguration(
                    f"libworhpmonitor.dll not found in {self._archive_dir}. "
                    f"Please download it from {self.conan_data['worhpmonitor'][0]['url']} and place it there."
                )


    def _extract_deb(self, deb_file, dst):
        self._utils.extract_deb(deb_file, dst)

    def _source(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            # There's also a .zip archive, but it depends on a very old libgfortran.so.3 from GCC 7.
            self._extract_deb(self._archive_path, self.source_folder)
            move_folder_contents(self, os.path.join(self.source_folder, "usr"), self.source_folder)
        else:
            unzip(self, self._archive_path, destination=self.source_folder)

    def build(self):
        self._source()

    def package(self):
        # No license file is provided
        copy(self, "*.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        if self.settings.os == "Windows":
            if self.settings.compiler == "msvc":
                copy(self, "worhp.lib", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
            else:
                copy(self, "worhp.dll.a", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
            copy(self, "*.dll", os.path.join(self.source_folder, "bin"), os.path.join(self.package_folder, "bin"))
        else:
            copy(self, "libworhp.so", os.path.join(self.source_folder, "lib"), os.path.join(self.package_folder, "lib"))
        if self.options.tools:
            copy(self, "*", os.path.join(self.source_folder, "bin"), os.path.join(self.package_folder, "bin"))
        if self.options.get_safe("worhpmonitor"):
            copy(self, "libworhpmonitor.dll", self._archive_dir, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "WORHP")
        self.cpp_info.set_property("cmake_target_name", "WORHP::WORHP")
        self.cpp_info.set_property("nosoname", True)
        self.cpp_info.libs = ["worhp"]
        self.cpp_info.includedirs.append("include/worhp")
