import hashlib
import os
import re
import shutil
import textwrap
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building, stdcpp_library, check_min_cppstd
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc, unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.1.0"


class ICUConan(ConanFile):
    name = "icu"
    homepage = "http://site.icu-project.org"
    license = "Unicode-3.0"
    description = "ICU is a mature, widely used set of C/C++ and Java libraries " \
                  "providing Unicode and Globalization support for software applications."
    topics = ("icu4c", "i see you", "unicode")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "data_packaging": ["files", "archive", "library", "static"],
        "with_dyload": [True, False],
        "dat_package_file": [None, "ANY"],
        "with_icuio": [True, False],
        "with_extras": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "data_packaging": "archive",
        "with_dyload": True,
        "dat_package_file": None,
        "with_icuio": True,
        "with_extras": False,
    }

    @property
    def _enable_icu_tools(self):
        return self.settings.os not in ["iOS", "tvOS", "watchOS", "Emscripten"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.data_packaging

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.options.dat_package_file:
            if not os.path.exists(str(self.options.dat_package_file)):
                raise ConanInvalidConfiguration("Non-existent dat_package_file specified")
        if Version(self.version) >= "75.1":
            check_min_cppstd(self, 17)

    def layout(self):
        basic_layout(self, src_folder="src")

    @staticmethod
    def _sha256sum(file_path):
        m = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for data in iter(lambda: fh.read(8192), b""):
                m.update(data)
        return m.hexdigest()

    def package_id(self):
        if self.info.options.dat_package_file:
            self.info.options.dat_package_file = self._sha256sum(str(self.info.options.dat_package_file))

    def build_requirements(self):
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/latest")

        if cross_building(self):
            self.tool_requires(str(self.ref))

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        self._patch_sources()

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.extra_defines.append("U_STATIC_IMPLEMENTATION")
        if is_apple_os(self):
            tc.extra_defines.append("_DARWIN_C_SOURCE")
        yes_no = lambda v: "yes" if v else "no"
        tc.configure_args.extend([
            "--datarootdir=${prefix}/share",
            f"--enable-release={yes_no(self.settings.build_type != 'Debug')}",
            f"--enable-debug={yes_no(self.settings.build_type == 'Debug')}",
            f"--enable-dyload={yes_no(self.options.with_dyload)}",
            f"--enable-extras={yes_no(self.options.with_extras)}",
            f"--enable-icuio={yes_no(self.options.with_icuio)}",
            "--disable-layoutex",
            "--disable-layout",
            f"--enable-tools={yes_no(self._enable_icu_tools)}",
            "--disable-tests",
            "--disable-samples",
        ])
        if cross_building(self):
            base_path = unix_path(self, self.dependencies.build["icu"].package_folder)
            tc.configure_args.append(f"--with-cross-build={base_path}")
            if self.settings.os in ["iOS", "tvOS", "watchOS"]:
                # ICU build scripts interpret all Apple platforms as 'darwin'.
                # Since this can coincide with the `build` triple, we need to tweak
                # the build triple to avoid the collision and ensure the scripts
                # know we are cross-building.
                host_triplet = f"{str(self.settings.arch)}-apple-darwin"
                build_triplet = f"{str(self.settings_build.arch)}-apple"
                tc.update_configure_args({"--host": host_triplet,
                                          "--build": build_triplet})
        else:
            arch64 = ["x86_64", "sparcv9", "ppc64", "ppc64le", "armv8", "armv8.3", "mips64"]
            bits = "64" if self.settings.arch in arch64 else "32"
            tc.configure_args.append(f"--with-library-bits={bits}")
        if self.settings.os != "Windows":
            # http://userguide.icu-project.org/icudata
            # This is the only directly supported behavior on Windows builds.
            tc.configure_args.append(f"--with-data-packaging={self.options.data_packaging}")
        tc.generate()

        if is_msvc(self):
            env = Environment()
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            if cross_building(self):
                env.define("icu_cv_host_frag", "mh-msys-msvc")
            env.vars(self).save_script("conanbuild_icu_msvc")

    def _patch_sources(self):
        # Prevent any call to python during configuration, it's only needed for unit tests
        replace_in_file(self, os.path.join(self.source_folder, "source", "configure"),
                        'if test -z "$PYTHON"',
                        "if true")

        if self.settings_build.os == "Windows":
            # https://unicode-org.atlassian.net/projects/ICU/issues/ICU-20545
            makeconv_cpp = os.path.join(self.source_folder, "source", "tools", "makeconv", "makeconv.cpp")
            replace_in_file(self, makeconv_cpp,
                            "pathBuf.appendPathPart(arg, localError);",
                            "pathBuf.append(\"/\", localError); pathBuf.append(arg, localError);")

        # relocatable shared libs on macOS
        mh_darwin = os.path.join(self.source_folder, "source", "config", "mh-darwin")
        replace_in_file(self, mh_darwin, "-install_name $(libdir)/$(notdir", "-install_name @rpath/$(notdir")
        replace_in_file(self,
            mh_darwin,
            "-install_name $(notdir $(MIDDLE_SO_TARGET)) $(PKGDATA_TRAILING_SPACE)",
            "-install_name @rpath/$(notdir $(MIDDLE_SO_TARGET))",
        )

    def build(self):
        # workaround for https://unicode-org.atlassian.net/browse/ICU-20531
        mkdir(self, os.path.join(self.build_folder, "data", "out", "tmp"))

        # workaround for "No rule to make target 'out/tmp/dirs.timestamp'"
        save(self, os.path.join(self.build_folder, "data", "out", "tmp", "dirs.timestamp"), "")

        if self.options.dat_package_file:
            dat_package_file = list(Path(self.source_folder, "source", "data", "in").glob("*.dat"))
            if dat_package_file:
                shutil.copy(str(self.options.dat_package_file), dat_package_file[0])

        autotools = Autotools(self)
        autotools.configure(build_script_folder="source")
        autotools.make()

    @property
    def _data_stem(self):
        vtag = Version(self.version).major
        arch = self.settings.get_safe("arch")
        suffix = "b" if arch in {"ppc32", "ppc64",
                                 "sparc", "sparcv9",
                                 "s390", "s390x",
                                 "mips", "mips64"} else "l"
        return f"icudt{vtag}{suffix}"

    @property
    def _data_filename(self):
        return self._data_stem + ".dat"

    @property
    def _data_dir_name(self):
        if self.settings.os == "Windows" and self.settings.build_type == "Debug":
            return "icud"
        return "icu"

    @property
    def _data_path(self):
        return os.path.join(self.package_folder, "share", self._data_dir_name, str(self.version), self._data_filename)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

        bin_dir = Path(self.package_folder, "bin")
        for dll in Path(self.package_folder, "lib").glob("*.dll"):
            bin_dir.mkdir(exist_ok=True)
            rm(self, dll.name, bin_dir)
            rename(self, dll, bin_dir / dll.name)

        # Copy some files required for cross-compiling
        config_dir = os.path.join(self.package_folder, "config")
        copy(self, "icucross.mk", src=os.path.join(self.build_folder, "config"), dst=config_dir)
        copy(self, "icucross.inc", src=os.path.join(self.build_folder, "config"), dst=config_dir)

        rmdir(self, os.path.join(self.package_folder, "lib", "man"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))

    @property
    def _unicode_version(self):
        header = load(self, os.path.join(self.package_folder, "include", "unicode", "uchar.h"))
        return re.search(r'U_UNICODE_VERSION "(.+?)"', header).group(1)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "ICU")

        prefix = "s" if self.settings.os == "Windows" and not self.options.shared else ""
        suffix = "d" if self.settings.os == "Windows" and self.settings.build_type == "Debug" else ""

        # https://github.com/unicode-org/icu/blob/release-76-1/icu4c/source/config/icu.pc.in#L5-L32
        # Assume that the build flags will be taken from the normal pkg-config Cflags etc.
        pkg_config_extra = textwrap.dedent(f"""\
            CFLAGS =
            CXXFLAGS =
            DEFS =
            baselibs =
            UNICODE_VERSION={self._unicode_version}
            ICUPREFIX=icu
            ICULIBSUFFIX={suffix}
            LIBICU=libicu
            pkglibdir=${{prefix}}/share
            ICUDATA_NAME = {self._data_stem}
            ICUDESC=International Components for Unicode
        """)

        # icudata
        self.cpp_info.components["icu-data"].set_property("cmake_target_name", "ICU::data")
        self.cpp_info.components["icu-data"].set_property("cmake_target_aliases", ["ICU::dt"])
        icudata_libname = "icudt" if self.settings.os == "Windows" else "icudata"
        self.cpp_info.components["icu-data"].libs = [f"{prefix}{icudata_libname}{suffix}"]
        if not self.options.shared:
            self.cpp_info.components["icu-data"].defines.append("U_STATIC_IMPLEMENTATION")
            # icu uses c++, so add the c++ runtime
            libcxx = stdcpp_library(self)
            if libcxx:
                self.cpp_info.components["icu-data"].system_libs.append(libcxx)

        # icuuc
        self.cpp_info.components["icu-uc"].set_property("cmake_target_name", "ICU::uc")
        self.cpp_info.components["icu-uc"].set_property("pkg_config_name", "icu-uc")
        self.cpp_info.components["icu-uc"].set_property("pkg_config_custom_content", pkg_config_extra)
        self.cpp_info.components["icu-uc"].libs = [f"{prefix}icuuc{suffix}"]
        self.cpp_info.components["icu-uc"].resdirs = [os.path.join("lib", self._data_dir_name)]
        self.cpp_info.components["icu-uc"].requires = ["icu-data"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["icu-uc"].system_libs = ["m", "pthread"]
            if self.options.with_dyload:
                self.cpp_info.components["icu-uc"].system_libs.append("dl")
        elif self.settings.os == "Windows":
            self.cpp_info.components["icu-uc"].system_libs = ["advapi32"]

        # icui18n
        self.cpp_info.components["icu-i18n"].set_property("cmake_target_name", "ICU::i18n")
        self.cpp_info.components["icu-i18n"].set_property("cmake_target_aliases", ["ICU::in"])
        self.cpp_info.components["icu-i18n"].set_property("pkg_config_name", "icu-i18n")
        self.cpp_info.components["icu-i18n"].set_property("pkg_config_custom_content", pkg_config_extra)
        icui18n_libname = "icuin" if self.settings.os == "Windows" else "icui18n"
        self.cpp_info.components["icu-i18n"].libs = [f"{prefix}{icui18n_libname}{suffix}"]
        self.cpp_info.components["icu-i18n"].requires = ["icu-uc"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["icu-i18n"].system_libs = ["m"]

        # icuio
        if self.options.with_icuio:
            self.cpp_info.components["icu-io"].set_property("cmake_target_name", "ICU::io")
            self.cpp_info.components["icu-io"].set_property("pkg_config_name", "icu-io")
            self.cpp_info.components["icu-io"].set_property("pkg_config_custom_content", pkg_config_extra)
            self.cpp_info.components["icu-io"].libs = [f"{prefix}icuio{suffix}"]
            self.cpp_info.components["icu-io"].requires = ["icu-i18n", "icu-uc"]

        if self.settings.os != "Windows" and self.options.data_packaging in ["files", "archive"]:
            self.cpp_info.components["icu-data"].resdirs = ["share"]
            data_path = self._data_path.replace("\\", "/")
            self.runenv_info.prepend_path("ICU_DATA", data_path)
            if self._enable_icu_tools or self.options.with_extras:
                self.buildenv_info.prepend_path("ICU_DATA", data_path)

        if self._enable_icu_tools:
            # icutu
            self.cpp_info.components["icu-tu"].set_property("cmake_target_name", "ICU::tu")
            self.cpp_info.components["icu-tu"].libs = [f"{prefix}icutu{suffix}"]
            self.cpp_info.components["icu-tu"].requires = ["icu-i18n", "icu-uc"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["icu-tu"].system_libs = ["pthread"]

            # icutest
            self.cpp_info.components["icu-test"].set_property("cmake_target_name", "ICU::test")
            self.cpp_info.components["icu-test"].libs = [f"{prefix}icutest{suffix}"]
            self.cpp_info.components["icu-test"].requires = ["icu-tu", "icu-uc"]
