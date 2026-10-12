import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.4"


class GdkPixbufConan(ConanFile):
    name = "gdk-pixbuf"
    description = "toolkit for image loading and pixel buffer manipulation"
    topics = ("image",)
    homepage = "https://developer.gnome.org/gdk-pixbuf/"
    license = "LGPL-2.1-or-later"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "with_libpng": [True, False],
        "with_libtiff": [True, False],
        "with_libjpeg": [True, False],
        "with_introspection": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "with_libpng": True,
        "with_libtiff": True,
        "with_libjpeg": True,
        "with_introspection": False,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    python_requires = "conan-utils/latest"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.shared:
            self.options["glib"].shared = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_introspection:
            self.requires("glib-gir/[^2.82]")
        if self.options.with_libpng:
            self.requires("libpng/[~1.6]")
        if self.options.with_libtiff:
            self.requires("libtiff/[>=4.5 <5]")
        if self.options.with_libjpeg:
            self.requires("libjpeg-meta/latest")

    def validate(self):
        if self.options.shared and not self.dependencies["glib"].options.shared:
            raise ConanInvalidConfiguration(
                "Linking a shared library against static glib can cause unexpected behaviour."
            )
        if self.dependencies["glib"].options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration(
                "Linking shared glib with the MSVC static runtime is not supported"
            )

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]", options={"tools": True})
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("glib/<host_version>")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/[^1.82]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _requires_compiler_rt(self):
        return self.settings.compiler == "clang" and Version(self.settings.compiler.version) <= "12" and self.settings.build_type == "Debug"

    def generate(self):
        if can_run(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        deps = PkgConfigDeps(self)
        deps.generate()

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        enabled_disabled = lambda v: "enabled" if v else "disabled"
        tc.project_options.update({
            "builtin_loaders": "all",
            "gio_sniffing": "false",
            "introspection": enabled_disabled(self.options.with_introspection),
            "docs": "false",
            "man": "false",
            "installed_tests": "false",
            "png": enabled_disabled(self.options.with_libpng),
            "tiff": enabled_disabled(self.options.with_libtiff),
            "jpeg": enabled_disabled(self.options.with_libjpeg)
        })
        # Workaround for https://bugs.llvm.org/show_bug.cgi?id=16404
        # Only really for the purposes of building on CCI - end users can
        # workaround this by appropriately setting global linker flags in their profile
        if self._requires_compiler_rt:
            tc.c_link_args.append("-rtlib=compiler-rt")
        tc.generate()

    def _patch_sources(self):
        meson_build = os.path.join(self.source_folder, "meson.build")
        gdk_meson_build = os.path.join(self.source_folder, "gdk-pixbuf", "meson.build")

        replace_in_file(self, meson_build, "subdir('tests')", "#subdir('tests')")
        replace_in_file(self, meson_build, "subdir('thumbnailer')", "#subdir('thumbnailer')")
        replace_in_file(self, meson_build, "gmodule_dep.get_variable(pkgconfig: 'gmodule_supported')", "'true'")
        # workaround https://gitlab.gnome.org/GNOME/gdk-pixbuf/-/issues/203
        replace_in_file(self, os.path.join(self.source_folder, "build-aux", "post-install.py"),
                        "close_fds=True", "close_fds=(sys.platform != 'win32')")
        replace_in_file(self, meson_build, "is_msvc_like = ", "is_msvc_like = false #")
        # Fix libtiff and libpng not being linked against when building statically
        # Reported upstream: https://gitlab.gnome.org/GNOME/gdk-pixbuf/-/merge_requests/159
        replace_in_file(self, gdk_meson_build,
                        "dependencies: gdk_pixbuf_deps + [ gdkpixbuf_dep ],",
                        "dependencies: loaders_deps + gdk_pixbuf_deps + [ gdkpixbuf_dep ],")
        # Forcing Conan libgettext instead of system one (if OS != Linux)
        if self.settings.os != "Linux":
            # FIXME: unify libgettext and gettext ??
            replace_in_file(self, meson_build,
                            "intl_dep = cc.find_library('intl', required: false)",
                            "intl_dep = dependency('libgettext', version: '>=0.21', required: false, method: 'pkg-config')")
        if self.settings.os == "Macos" and self.options.shared:
            # Workaround to avoid generating gdk-pixbuf/loaders.cache fails
            # Error output:
            #   [167/167] Generating gdk-pixbuf/loaders.cache with a custom command (wrapped by meson to capture output)
            #   FAILED: gdk-pixbuf/loaders.cache
            #   meson.py --internal exe --capture gdk-pixbuf/loaders.cache -- xxxx/gdk-pixbuf/gdk-pixbuf-query-loaders
            #   --- stderr ---
            #   dyld[25158]: Library not loaded: /lib/libgnuintl.8.dylib
            #   Reason: tried: '/lib/libgnuintl.8.dylib' (no such file), '/System/Volumes/Preboot/Cryptexes/OS/lib/libgnuintl.8.dylib' (no such file)
            #
            # Obviously, the libgnuintl.8.dylib is in the VirtualRunEnv, but the current env is not passed to
            # the meson custom_target function as it's wrappering the execution
            # custom_target admits also an "env" parameter, but it's not working as expected
            replace_in_file(self, gdk_meson_build, "build_by_default: true", "build_by_default: false")

        if not self.options.i18n:
            save(self, os.path.join(self.source_folder, "po", "meson.build"), "")

    def build(self):
        self._patch_sources()
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)
        fix_apple_shared_install_name(self)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "gdk-pixbuf-2.0")
        self.cpp_info.libs = ["gdk_pixbuf-2.0"]
        self.cpp_info.includedirs = [os.path.join("include", "gdk-pixbuf-2.0")]
        self.cpp_info.resdirs = ["share"]
        if not self.options.shared:
            self.cpp_info.defines.append("GDK_PIXBUF_STATIC_COMPILATION")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
        if self._requires_compiler_rt:
            ldflags = ["-rtlib=compiler-rt"]
            self.cpp_info.exelinkflags = ldflags
            self.cpp_info.sharedlinkflags = ldflags
        if self.options.i18n:
            self.cpp_info.resdirs = ["share"]

        self.cpp_info.requires = [
            "glib::gobject-2.0",
            "glib::glib-2.0",
            "glib::gmodule-no-export-2.0",
            "glib::gio-2.0"
        ]
        if self.options.with_libpng:
            self.cpp_info.requires.append("libpng::libpng")
        if self.options.with_libtiff:
            self.cpp_info.requires.append("libtiff::tiff")
        if self.options.with_libjpeg:
            self.cpp_info.requires.append("libjpeg-meta::jpeg")

        # Breaking change since Conan >= 2.0.8
        # Related to https://github.com/conan-io/conan/pull/14233
        libdir_variable = "libdir"
        pkgconfig_variables = {
            "bindir": "${prefix}/bin",
            "gdk_pixbuf_binary_version": "2.10.0",
            "gdk_pixbuf_binarydir": "${%s}/gdk-pixbuf-2.0/2.10" % libdir_variable,
            "gdk_pixbuf_moduledir": "${gdk_pixbuf_binarydir}/loaders",
            "gdk_pixbuf_cache_file": "${gdk_pixbuf_binarydir}/loaders.cache",
            "gdk_pixbuf_csource": "${bindir}/gdk-pixbuf-csource",
            "gdk_pixbuf_pixdata": "${bindir}/gdk-pixbuf-pixdata",
            "gdk_pixbuf_query_loaders": "${bindir}/gdk-pixbuf-query-loaders"
        }
        self.cpp_info.set_property(
            "pkg_config_custom_content",
            "\n".join(f"{key}={value}" for key, value in pkgconfig_variables.items()))

        gdk_pixbuf_pixdata = os.path.join(self.package_folder, "bin", "gdk-pixbuf-pixdata")
        self.runenv_info.define_path("GDK_PIXBUF_PIXDATA", gdk_pixbuf_pixdata)

        if self.options.with_introspection:
            self.cpp_info.requires.append("glib-gir::glib-gir")
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))
