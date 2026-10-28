import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path

required_conan_version = ">=2.13"


class OoqpConan(ConanFile):
    name = "ooqp"
    description = "Object-Oriented Quadratic Programming solver"
    license = "DocumentRef-COPYRIGHT:LicenseRef-OOQP"
    homepage = "https://github.com/emgertz/OOQP"
    topics = ("optimization", "quadratic-programming", "interior-point", "sparse-linear-algebra")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
    }
    default_options = {
        "fPIC": True,
    }

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("lapack/latest")
        self.requires("coin-hsl/[*]")

    def validate(self):
        mangling = self.dependencies["lapack"].extension_properties["fortran_name_mangling"]
        if mangling != "lower_underscore":
            raise ConanInvalidConfiguration("OOQP requires BLAS/LAPACK with lower_underscore names")

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("BLAS= ")
        tc.configure_args.append("MA27LIB=-lcoinhsl")
        tc.configure_args.append("MA57LIB=-lcoinhsl")
        tc.make_args.append(f"prefix={unix_path(self, self.package_folder)}")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "COPYRIGHT", self.source_folder, os.path.join(self.package_folder, "licenses"))
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install(target="install_libs")
            autotools.install(target="install_headers")
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        # Base OOQP library
        self.cpp_info.components["ooqpbase"].libs = ["ooqpbase"]
        self.cpp_info.components["ooqpbase"].requires.append("lapack::lapack")
        self.cpp_info.components["ooqpbase"].requires.append("coin-hsl::coin-hsl")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["ooqpbase"].system_libs = ["m", "pthread"]

        # Dense linear algebra backend
        self.cpp_info.components["ooqpdense"].libs = ["ooqpdense"]
        self.cpp_info.components["ooqpdense"].requires = ["ooqpbase"]

        # Sparse linear algebra backend
        self.cpp_info.components["ooqpsparse"].libs = ["ooqpsparse"]
        self.cpp_info.components["ooqpsparse"].requires = ["ooqpbase"]

        # QP formulation libraries
        self.cpp_info.components["ooqpgendense"].libs = ["ooqpgendense"]
        self.cpp_info.components["ooqpgendense"].requires = ["ooqpbase", "ooqpdense"]

        self.cpp_info.components["ooqpgensparse"].libs = ["ooqpgensparse"]
        self.cpp_info.components["ooqpgensparse"].requires = ["ooqpbase", "ooqpsparse"]

        self.cpp_info.components["ooqpbound"].libs = ["ooqpbound"]
        self.cpp_info.components["ooqpbound"].requires = ["ooqpbase"]

        # Solver libraries
        self.cpp_info.components["ooqpmehrotra"].libs = ["ooqpmehrotra"]
        self.cpp_info.components["ooqpmehrotra"].requires = ["ooqpbase"]

        self.cpp_info.components["ooqpgondzio"].libs = ["ooqpgondzio"]
        self.cpp_info.components["ooqpgondzio"].requires = ["ooqpbase"]

