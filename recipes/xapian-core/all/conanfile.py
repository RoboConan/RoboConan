import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools import CppInfo
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.1"


class XapianCoreConan(ConanFile):
    name = "xapian-core"
    description = (
        "Xapian is a highly adaptable toolkit which allows developers to easily "
        "add advanced indexing and search facilities to their own applications."
    )
    topics = ("xapian", "search", "engine", "indexing", "query")
    license = "GPL-2.0-or-later"
    homepage = "https://xapian.org/"

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

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib-ng/[^2.0]")
        if self.settings.os != "Windows":
            self.requires("util-linux-libuuid/[^2.41]")

    def validate(self):
        if self.options.shared and self.settings.os == "Windows":
            raise ConanInvalidConfiguration(
                "shared builds are unavailable due to libtool's inability to create shared libraries"
            )

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        tc = AutotoolsToolchain(self)
        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
        tc.configure_args.extend([
            "--disable-documentation",
        ])
        env = tc.environment()
        if is_msvc(self):
            msvc_cl_sh = unix_path(self, os.path.join(self.source_folder, "msvc_cl.sh"))
            env.define("AR", "lib")
            env.define("CC", msvc_cl_sh)
            env.define("CXX", msvc_cl_sh)
            env.define("LD", msvc_cl_sh)
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")

        if is_apple_os(self) and self.settings.arch == "armv8":
            # A fix for ./configure issues on armv8
            tc.configure_args.append("--host=aarch64-apple-darwin")
            tc.extra_ldflags.append("-arch arm64")

        tc.generate(env)

        if is_msvc(self):
            # Custom AutotoolsDeps for cl like compilers
            # workaround for https://github.com/conan-io/conan/issues/12784
            cpp_info = CppInfo(self)
            for dependency in reversed(self.dependencies.host.topological_sort.values()):
                cpp_info.merge(dependency.cpp_info.aggregated_components())
            env = Environment()
            env.append("CPPFLAGS", [f"-I{unix_path(self, p)}" for p in cpp_info.includedirs] + [f"-D{d}" for d in cpp_info.defines])
            env.append("_LINK_", [lib if lib.endswith(".lib") else f"{lib}.lib" for lib in cpp_info.libs])
            env.append("LDFLAGS", [f"-L{unix_path(self, p)}" for p in cpp_info.libdirs] + cpp_info.sharedlinkflags + cpp_info.exelinkflags)
            env.append("CXXFLAGS", cpp_info.cxxflags)
            env.append("CFLAGS", cpp_info.cflags)
            env.vars(self).save_script("conanautotoolsdeps_cl_workaround")
        else:
            deps = AutotoolsDeps(self)
            deps.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

        if is_msvc(self) and not self.options.shared:
            rename(self, f"{self.package_folder}/lib/libxapian.lib",
                         f"{self.package_folder}/lib/xapian.lib")

        rm(self, "xapian-config", f"{self.package_folder}/bin")
        rm(self, "*.la", f"{self.package_folder}/lib")
        rmdir(self, f"{self.package_folder}/lib/cmake")
        rmdir(self, f"{self.package_folder}/lib/pkgconfig")
        rmdir(self, f"{self.package_folder}/share/doc")
        rmdir(self, f"{self.package_folder}/share/man")
        fix_apple_shared_install_name(self)

        self._create_cmake_module_variables(
            f"{self.package_folder}/{self._module_file_rel_path}"
        )

    def _create_cmake_module_variables(self, module_file):
        content = textwrap.dedent("""\
            set(XAPIAN_FOUND TRUE)
            set(XAPIAN_INCLUDE_DIR ${xapian_INCLUDE_DIR}
                                   ${xapian_INCLUDE_DIR_RELEASE}
                                   ${xapian_INCLUDE_DIR_RELWITHDEBINFO}
                                   ${xapian_INCLUDE_DIR_MINSIZEREL}
                                   ${xapian_INCLUDE_DIR_DEBUG})
            set(XAPIAN_LIBRARIES ${xapian_LIBRARIES}
                                 ${xapian_LIBRARIES_RELEASE}
                                 ${xapian_LIBRARIES_RELWITHDEBINFO}
                                 ${xapian_LIBRARIES_MINSIZEREL}
                                 ${xapian_LIBRARIES_DEBUG})
        """)
        save(self, module_file, content)

    @property
    def _module_file_rel_path(self):
        return f"lib/cmake/conan-official-{self.name}-variables.cmake"

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "xapian")
        self.cpp_info.set_property("cmake_build_modules", [self._module_file_rel_path])
        self.cpp_info.set_property("pkg_config_name", "xapian-core")
        self.cpp_info.libs = ["xapian"]
        self.cpp_info.resdirs = ["share"]
        if not self.options.shared:
            if self.settings.os in ("Linux", "FreeBSD"):
                self.cpp_info.system_libs = ["rt", "m"]
            elif self.settings.os == "Windows":
                self.cpp_info.system_libs = ["rpcrt4", "ws2_32"]
            elif self.settings.os == "SunOS":
                self.cpp_info.system_libs = ["socket", "nsl"]

        xapian_aclocal_dir = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.prepend_path("ACLOCAL_PATH", xapian_aclocal_dir)
