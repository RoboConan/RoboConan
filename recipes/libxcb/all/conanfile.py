import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps, AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.4"


class LibXcbConan(ConanFile):
    name = "libxcb"
    description = "X protocol C-language Binding (XCB) library"
    license = "X11-distribute-modifications-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxcb"
    topics = ("xorg", "x11", "xcb")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_dri3_ext": [True, False],
        "build_ge_ext": [True, False],
        "build_xevie_ext": [True, False],
        "build_xprint_ext": [True, False],
        "build_xselinux_ext": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_dri3_ext": True,
        # Disabled by default
        "build_ge_ext": False,
        "build_xevie_ext": False,
        "build_xprint_ext": False,
        "build_xselinux_ext": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libxau/[^1.0.12]")
        self.requires("libxdmcp/[^1.1.5]")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration("MSVC is not supported.")

    @property
    def _have_python(self):
        return not getattr(sys, "frozen", False)

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")
        self.tool_requires("xcb-proto/[^1.17.0]")
        if not self._have_python:
            self.tool_requires("cpython/[>=3.12 <3.13]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

        yes_no = lambda v: "yes" if v else "no"
        tc = AutotoolsToolchain(self)
        if not self._have_python:
            python_path = os.path.join(self.dependencies.build["cpython"].cpp_info.bindir, "python3")
            tc.configure_args.append(f"PYTHON={unix_path(self, python_path)}")
        tc.configure_args.extend([
            "HAVE_CHECK=no",
            "--with-doxygen=no",
            "--disable-devel-docs",
            # Default extensions
            "--enable-composite=yes",
            "--enable-damage=yes",
            "--enable-dbe=yes",
            "--enable-dpms=yes",
            "--enable-dri2=yes",
            "--enable-glx=yes",
            "--enable-present=yes",
            "--enable-randr=yes",
            "--enable-record=yes",
            "--enable-render=yes",
            "--enable-resource=yes",
            "--enable-screensaver=yes",
            "--enable-shape=yes",
            "--enable-shm=yes",
            "--enable-sync=yes",
            "--enable-xevie=yes",
            "--enable-xfixes=yes",
            "--enable-xfree86=yes",
            "--enable-xinerama=yes",
            "--enable-xinput=yes",
            "--enable-xkb=yes",
            "--enable-xprint=yes",
            "--enable-selinux=yes",
            "--enable-xtest=yes",
            "--enable-xv=yes",
            "--enable-xvmc=yes",
            # Optional extensions
            f"--enable-dri3={yes_no(self.options.build_dri3_ext)}",
            f"--enable-ge={yes_no(self.options.build_ge_ext)}",
            f"--enable-xevie={yes_no(self.options.build_xevie_ext)}",
            f"--enable-xprint={yes_no(self.options.build_xprint_ext)}",
            f"--enable-selinux={yes_no(self.options.build_xselinux_ext)}",
        ])
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.build_context_activated = ["xcb-proto"]
        deps.generate()

        # Write a .pc file to mock the simple libpthread-stubs meta-package.
        # https://gitlab.freedesktop.org/xorg/lib/pthread-stubs/-/blob/libpthread-stubs-0.5/configure.ac#L29-36
        save(self, os.path.join(self.generators_folder, "pthread-stubs.pc"),
             "Version: 0.5\n"
             "Cflags: -pthread\n"
             "Libs: ")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "_xcb_do_not_use")

        self.cpp_info.components["xcb"].set_property("pkg_config_name", "xcb")
        self.cpp_info.components["xcb"].set_property("cmake_target_name", "X11::xcb")
        self.cpp_info.components["xcb"].libs = ["xcb"]
        self.cpp_info.components["xcb"].requires = ["libxau::libxau", "libxdmcp::libxdmcp"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["xcb"].system_libs = ["pthread"]

        xcbproto_version = self.dependencies.build["xcb-proto"].ref.version
        self.cpp_info.components["xcb"].set_property("pkg_config_custom_content", f"xcbproto_version={xcbproto_version}")

        def _add_extension(name):
            component = self.cpp_info.components[f"xcb-{name}"]
            component.set_property("pkg_config_name", f"xcb-{name}")
            component.set_property("cmake_target_name", f"X11::xcb_{name}")
            component.libs = [f"xcb-{name}"]
            component.requires = ["xcb"]

        _add_extension("composite")
        _add_extension("damage")
        _add_extension("dbe")
        _add_extension("dpms")
        _add_extension("dri2")
        _add_extension("glx")
        _add_extension("present")
        _add_extension("randr")
        _add_extension("record")
        _add_extension("render")
        _add_extension("res")
        _add_extension("screensaver")
        _add_extension("shape")
        _add_extension("shm")
        _add_extension("sync")
        _add_extension("xf86dri")
        _add_extension("xfixes")
        _add_extension("xinerama")
        _add_extension("xinput")
        _add_extension("xkb")
        _add_extension("xtest")
        _add_extension("xv")
        _add_extension("xvmc")

        if self.options.build_dri3_ext:
            _add_extension("dri3")
        if self.options.build_ge_ext:
            _add_extension("ge")
        if self.options.build_xevie_ext:
            _add_extension("xevie")
        if self.options.build_xprint_ext:
            _add_extension("xprint")
        if self.options.build_xselinux_ext:
            _add_extension("xselinux")
