import os
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class ArmPLConan(ConanFile):
    name = "armpl"
    description = ("Arm Performance Libraries provides optimized standard core math libraries"
                   " for numerical applications on 64-bit Arm based processors.")
    license = "DocumentRef-license_agreement.txt:LicenseRef-ArmPL-EULA"
    homepage = "https://developer.arm.com/Tools%20and%20Software/Arm%20Performance%20Libraries"
    topics = ("arm", "math", "blas", "lapack", "linear-algebra", "fft", "pre-built")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "interface": ["lp64", "ilp64"],
        "threading": ["seq", "omp"],
    }
    default_options = {
        "shared": False,
        "interface": "lp64",
        "threading": "omp",
    }
    extension_properties = {"fortran_name_mangling": "lower_underscore"}

    python_requires = "conan-utils/latest"

    @property
    def _utils(self):
        return self.python_requires["conan-utils"].module

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.threading == "omp":
            # transitive_headers=True for -fopenmp to be propagated
            self.requires("openmp/system", transitive_headers=True)

    @property
    def _platform(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            return "Linux"
        return None

    def validate(self):
        if self._platform is None:
            raise ConanInvalidConfiguration(f"ArmPL is not supported on {self.settings.os}")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("ArmPL is only available for armv8 (aarch64)")

    def _path_filter(self, path):
        if path.startswith("include"):
            return True
        if path.startswith("lib"):
            if self.options.shared and not ".so" in path:
                return False
            if not self.options.shared and not path.endswith(".a"):
                return False
            if "astring" in path or "amath" in path:
                return True
            if self.options.interface == "lp64" and "_ilp64" in path or "_int64" in path:
                return False
            elif self.options.interface == "ilp64" and "_lp64" in path:
                return False
            if self.options.threading == "omp":
                return "_mp" in path
            else:
                return "_mp" not in path
        return False

    def package(self):
        filename = "armpl.deb.tar"
        download(self, **self.conan_data["sources"][self.version][str(self.settings.os)], filename=filename)
        self.output.info("Extracting...")
        # Extract licenses
        license_dir = os.path.join(self.package_folder, "licenses")
        mkdir(self, license_dir)
        with tarfile.open(filename) as tar:
            members = []
            for m in tar.getmembers():
                if "license_terms" in m.name and m.name.endswith(".txt"):
                    m.path = os.path.basename(m.name)
                    members.append(m)
            tar.extractall(license_dir, members)
        # Extract library files
        ver_str = ".".join(self.version.split(".")[:2])
        extract_from_armpl_tar(
            self._utils,
            filename,
            "armpl_",
            f"/opt/arm/armpl_{ver_str}_gcc",
            self.package_folder,
            self._path_filter
        )
        os.unlink(filename)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "armpl")
        if self.options.threading == "omp":
            self.cpp_info.set_property("pkg_config_aliases", ["armpl_mp"])

        linking = "dynamic" if self.options.shared else "static"
        interface = self.options.interface.value
        threading = self.options.threading.value
        name = f"armpl-{linking}-{interface}-{threading}"
        libname = f"armpl_{interface}"
        if threading == "omp":
            libname += "_mp"

        component = self.cpp_info.components[name]
        component.set_property("pkg_config_name", name)
        component.set_property("nosoname", True)
        component.libs = [libname]
        if interface == "ilp64":
            component.defines = ["INTEGER64"]
        component.requires = ["amath", "astring"]
        if threading == "omp":
            component.requires.append("openmp::openmp")

        self.cpp_info.components["amath"].libs = ["amath"]
        self.cpp_info.components["amath"].set_property("nosoname", True)
        if self.settings.os in ["Linux", "FreeBSD"] and not self.options.shared:
            self.cpp_info.components["amath"].system_libs = ["m"]

        self.cpp_info.components["astring"].libs = ["astring"]
        self.cpp_info.components["astring"].set_property("nosoname", True)


def extract_from_armpl_tar(utils, outer_tar_path, deb_prefix, subdir, output_dir, path_filter=None):
    """
    Full pipeline:
    - Open outer .tar
    - Find *_deb.sh
    - Skip to payload marker
    - Open inner .tar.gz
    - Find .deb with given prefix
    - Open its data.tar.*
    - Extract only subdir into output_dir
    """
    with tarfile.open(outer_tar_path, "r") as outer:
        # Find the installer .sh
        sh_member = next(
            (m for m in outer if m.name.endswith("_deb.sh")), None
        )
        if not sh_member:
            raise ValueError(f"*_deb.sh not found inside {outer_tar_path}")

        with outer.extractfile(sh_member) as sh_stream:
            payload_stream = find_payload_in_sh(sh_stream)
            with tarfile.open(fileobj=payload_stream, mode="r:gz") as inner:
                for member in inner:
                    if member.name.startswith(deb_prefix) and member.name.endswith(".deb"):
                        with inner.extractfile(member) as deb_stream:
                            utils.extract_deb(deb_stream, output_dir, subdir, path_filter=path_filter)
                            return
                raise ValueError(f"No .deb starting with {deb_prefix} found")


def find_payload_in_sh(sh_stream, marker=b"__START_OF_PAYLOAD__\n"):
    """
    Advance sh_stream until just after the payload marker.
    Returns the same stream positioned at the start of the payload.
    """
    while True:
        line = sh_stream.readline()
        if not line:
            raise ValueError("Payload marker not found in .sh file")
        if line == marker:
            break
    # Now positioned right after marker
    return sh_stream
