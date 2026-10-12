import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class PangommConan(ConanFile):
    name = "pangomm"
    description = "pangomm is a C++ API for Pango: a library for layout and rendering of text."
    license = "LGPL-2.1"
    homepage = "https://gitlab.gnome.org/GNOME/pangomm"
    topics = "pango", "wrapper", "text rendering", "fonts", "freedesktop"
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

    python_requires = "conan-utils/latest"

    @property
    def _abi_version(self):
        return "2.48" if Version(self.version) >= "2.48.0" else "1.4"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("pango/[^1.54.0]", transitive_headers=True, transitive_libs=True)
        if self._abi_version == "2.48":
            self.requires("glibmm/[^2.78.1]", transitive_headers=True, transitive_libs=True)
            self.requires("cairomm/[^1.18.0]", transitive_headers=True, transitive_libs=True)
        else:
            self.requires("glibmm/[>=2 <2.68]", transitive_headers=True, transitive_libs=True)
            self.requires("cairomm/[>=1 <1.16]", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self._abi_version == "2.48":
            check_min_cppstd(self, 17)
        else:
            check_min_cppstd(self, 11)

    def build_requirements(self):
        self.tool_requires("meson/[^1]")
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/[<4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        tc.project_options["build-documentation"] = "false"
        tc.project_options["msvc14x-parallel-installable"] = "false"
        tc.project_options["libdir"] = "lib"
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def _patch_sources(self):
        # glibmm_generate_extra_defs library does not provide any standard way
        # for discovery, which is why pangomm uses "find_library" method instead
        # of "dependency". this patch adds a hint to where this library is
        glibmm_generate_extra_defs_dir = [
            os.path.join(self.dependencies["glibmm"].package_folder, libdir)
            for libdir in self.dependencies["glibmm"].cpp_info.aggregated_components().libdirs
        ]

        replace_in_file(self, os.path.join(self.source_folder, "tools", "extra_defs_gen", "meson.build"),
            "required: glibmm_dep.type_name() != 'internal',",
            f"required: glibmm_dep.type_name() != 'internal', dirs: {glibmm_generate_extra_defs_dir}")

        if is_msvc(self):
            # when using cpp_std=c++NM the /permissive- flag is added which
            # attempts enforcing standard conformant c++ code
            # the problem is that older versions of Windows SDK is not standard
            # conformant! see:
            # https://developercommunity.visualstudio.com/t/error-c2760-in-combaseapih-with-windows-sdk-81-and/185399
            replace_in_file(self, os.path.join(self.source_folder, "meson.build"),
                            "cpp_std=c++",
                            "cpp_std=vc++")

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
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"), recursive=True)
        self.python_requires["conan-utils"].module.fix_msvc_libnames(self)

    def package_info(self):
        pangomm_lib = f"pangomm-{self._abi_version}"
        self.cpp_info.components[pangomm_lib].set_property("pkg_config_name", pangomm_lib)
        self.cpp_info.components[pangomm_lib].set_property("pkg_config_custom_content", "gmmprocm4dir=${libdir}/%s/proc/m4" % pangomm_lib)
        self.cpp_info.components[pangomm_lib].libs = [pangomm_lib]
        self.cpp_info.components[pangomm_lib].includedirs += [
            os.path.join("include", pangomm_lib),
            os.path.join("lib", pangomm_lib, "include"),
        ]
        if self._abi_version == "2.48":
            self.cpp_info.components[pangomm_lib].requires = [
                "pango::pangocairo",
                "glibmm::glibmm-2.68",
                "glibmm::giomm-2.68",
                "cairomm::cairomm-1.16",
            ]
        else:
            self.cpp_info.components[pangomm_lib].requires = [
                "pango::pangocairo",
                "glibmm::glibmm-2.4",
                "glibmm::giomm-2.4",
                "cairomm::cairomm-1.0",
            ]
