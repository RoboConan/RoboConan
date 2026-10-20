import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain, Autotools
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, NMakeToolchain
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class MpdecimalConan(ConanFile):
    name = "mpdecimal"
    description = "mpdecimal is a package for correctly-rounded arbitrary precision decimal floating point arithmetic."
    license = "BSD-2-Clause"
    topics = ("multiprecision", "decimal")
    homepage = "http://www.bytereef.org/mpdecimal"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cxx": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cxx": True,
    }
    implements = ["auto_shared_fpic"]

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.cxx:
            self.settings.rm_safe("compiler.libcxx")
            self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")
        self.folders.build = "src"

    def validate(self):
        if is_msvc(self) and self.settings.arch not in ("x86", "x86_64"):
            raise ConanInvalidConfiguration(
                f"{self.ref} currently does not supported {self.settings.arch}. Contributions are welcomed")
        if self.options.cxx and Version(self.version) < "2.5.1":
            if self.options.shared and self.settings.os == "Windows":
                raise ConanInvalidConfiguration(
                    "A shared libmpdec++ is not possible on Windows (due to non-exportable thread local storage)")

    def build_requirements(self):
        if not is_msvc(self) and self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

        # drop tests
        rmdir(self, "tests")
        save(self, "tests/Makefile.in", "all:;\ninstall:;\n")
        rmdir(self, "tests++")
        save(self, "tests++/Makefile.in", "all:;\ninstall:;\n")

        # Remove hardcoded MSVC runtime flags
        for msvc_runtime_flag in ["/MTd", "/MDd", "/MT", "/MD"]:
            replace_in_file(self, "libmpdec/Makefile.vc", msvc_runtime_flag, "")
            replace_in_file(self, "libmpdec++/Makefile.vc", msvc_runtime_flag, "")

        # Use a namespaced DLL define to allow a static consuming libraries to link against a shared mpdecimal library
        if Version(self.version) >= "2.5.1":
            for filename in [
                "libmpdec++/decimal.cc",
                "libmpdec++/decimal.hh",
                "libmpdec/mpdecimal32vc.h",
                "libmpdec/mpdecimal64vc.h",
            ]:
                replace_in_file(self, filename, "defined(_DLL)", "defined(MPDECIMAL_DLL)")

    def generate(self):
        if is_msvc(self):
            tc = NMakeToolchain(self)
            if Version(self.version) >= "2.5.1" and self.options.shared:
                tc.extra_defines.append("MPDECIMAL_DLL")
            tc.generate()
        else:
            tc = AutotoolsToolchain(self)
            tc.configure_args.append("--enable-cxx" if self.options.cxx else "--disable-cxx")
            tc_env = tc.environment()
            tc_env.append("LDXXFLAGS", ["$LDFLAGS"])
            tc.generate(tc_env)

    def _build_msvc(self):
        libmpdec_folder = os.path.join(self.source_folder, "libmpdec")
        libmpdecpp_folder = os.path.join(self.source_folder, "libmpdec++")

        builds = [libmpdec_folder]
        if self.options.cxx:
            builds.append(libmpdecpp_folder)

        for build_dir in builds:
            copy(self, "Makefile.vc", build_dir, self.build_folder)
            rename(self, os.path.join(self.build_folder, "Makefile.vc"), os.path.join(build_dir, "Makefile"))

            with chdir(self, build_dir):
                self.run("nmake -f Makefile.vc MACHINE={machine} DEBUG={debug} DLL={dll}".format(
                    machine={"x86": "ppro", "x86_64": "x64"}[str(self.settings.arch)],
                    # FIXME: else, use ansi32 and ansi64
                    debug="1" if self.settings.build_type == "Debug" else "0",
                    dll="1" if self.options.shared else "0",
                ))

    def build(self):
        # Replace the default target with just the target we want
        target = "SHARED" if self.options.shared else "STATIC"
        for ext in ["vc", "in"]:
            replace_in_file(self, f"libmpdec/Makefile.{ext}", "default:", f"default: $(LIB{target}) #")
            replace_in_file(self, f"libmpdec++/Makefile.{ext}", "default:", f"default: $(LIB{target}_CXX) #")

        if is_msvc(self):
            self._build_msvc()
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        mpdecdir = os.path.join(self.source_folder, "libmpdec")
        mpdecppdir = os.path.join(self.source_folder, "libmpdec++")

        license_file = "LICENSE.txt" if Version(self.version) < "4.0.0" else "COPYRIGHT.txt"
        copy(self, license_file, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "vccompat.h", src=mpdecdir, dst=os.path.join(self.package_folder, "include")) # 2.5.0/MSVC only
        copy(self, "mpdecimal.h", src=mpdecdir, dst=os.path.join(self.package_folder, "include"))
        if self.options.cxx:
            copy(self, "decimal.hh", src=mpdecppdir, dst=os.path.join(self.package_folder, "include"))
        builddirs = [mpdecdir]
        if self.options.cxx:
            builddirs.append(mpdecppdir)
        for builddir in builddirs:
            for pattern in ["*.a", "*.so", "*.so.*", "*.dylib", "*.lib"]:
                copy(self, pattern, src=builddir, dst=os.path.join(self.package_folder, "lib"))
            copy(self, "*.dll", src=builddir, dst=os.path.join(self.package_folder, "bin"))

    @property
    def _lib_pre_suf(self):
        if is_msvc(self):
            if self.options.shared:
                return "lib", f"-{self.version}.dll"
            else:
                return "lib", f"-{self.version}"
        elif self.settings.os == "Windows":
            if self.options.shared:
                return "", ".dll"
        return "", ""

    def package_info(self):
        prefix, suffix = self._lib_pre_suf
        self.cpp_info.components["libmpdecimal"].set_property("pkg_config_name", "libmpdec")
        self.cpp_info.components["libmpdecimal"].libs = [f"{prefix}mpdec{suffix}"]
        if self.options.shared and is_msvc(self):
            define = "MPDECIMAL_DLL" if Version(self.version) >= "2.5.1" else "USE_DLL"
            self.cpp_info.components["libmpdecimal"].defines = [define]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["libmpdecimal"].system_libs = ["m"]

        if self.options.cxx:
            self.cpp_info.components["libmpdecimal++"].set_property("pkg_config_name", "libmpdec++")
            self.cpp_info.components["libmpdecimal++"].libs = [f"{prefix}mpdec++{suffix}"]
            self.cpp_info.components["libmpdecimal++"].requires = ["libmpdecimal"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["libmpdecimal++"].system_libs = ["pthread"]
