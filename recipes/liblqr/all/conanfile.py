import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class LibLqrConan(ConanFile):
    name = "liblqr"
    description = (
        "The LiquidRescale (lqr) library provides a C/C++ API for performing "
        "non-uniform resizing of images by the seam-carving technique."
    )
    license = "LGPL-3.0-only"
    homepage = "http://liblqr.wikidot.com"
    topics = ("image", "resizing", "seam-carving")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    @property
    def _is_cl_like(self):
        return self.settings.compiler.get_safe("runtime") is not None

    def export_sources(self):
        copy(self, "CMakeLists.txt", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        if self._is_cl_like:
            cmake_layout(self, src_folder="src")
        else:
            basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]", transitive_headers=True)

    def build_requirements(self):
        if not self._is_cl_like:
            if not self.conf.get("tools.gnu:pkg_config", check_type=str):
                self.tool_requires("pkgconf/[<4]")
            if self.settings_build.os == "Windows":
                self.win_bash = True
                if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                    self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        if self._is_cl_like:
            tc = CMakeToolchain(self)
            tc.variables["LQR_SRC_DIR"] = self.source_folder.replace("\\", "/")
            tc.generate()
            deps = CMakeDeps(self)
            deps.generate()
        else:
            env = VirtualBuildEnv(self)
            env.generate()

            tc = AutotoolsToolchain(self)
            yes_no = lambda v: "yes" if v else "no"
            tc.configure_args.append("--disable-install-man")
            if self.settings.os == "Windows":
                # This option in upstream configure.ac must be disabled for static
                # windows build, to avoid adding __declspec(dllexport) in front
                # of declarations during build.
                tc.configure_args.append(f"--enable-declspec={yes_no(self.options.shared)}")
            tc.generate()

            deps = PkgConfigDeps(self)
            deps.generate()

    def build(self):
        if self._is_cl_like:
            cmake = CMake(self)
            cmake.configure(build_script_folder="..")
            cmake.build()
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self._is_cl_like:
            cmake = CMake(self)
            cmake.install()
        else:
            autotools = Autotools(self)
            autotools.install()
            rm(self, "*.la", os.path.join(self.package_folder, "lib"))
            rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
            fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "lqr-1")
        self.cpp_info.includedirs = [os.path.join("include", "lqr-1")]
        self.cpp_info.libs = ["lqr-1"]
        self.cpp_info.requires = ["glib::glib-2.0"]
        if self.settings.os == "Windows" and not self.options.shared:
            self.cpp_info.defines.append("LQR_DISABLE_DECLSPEC")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
