import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps, Autotools
from conan.tools.microsoft import is_msvc, unix_path
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class FlintConan(ConanFile):
    name = "flint"
    description = "FLINT (Fast Library for Number Theory)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.flintlib.org"
    topics = ("math", "numerical")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "memory_manager": ["single", "reentrant", "gc"],
        "with_blas": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "memory_manager": "reentrant",
        "with_blas": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("gmp/[^6.2.1]", transitive_headers=True, transitive_libs=True)
        self.requires("mpfr/[^4.1.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_blas:
            self.requires("blas/latest")
        if self.options.memory_manager == "gc":
            self.requires("bdwgc/[^8.2]", transitive_headers=True)
        if is_msvc(self):
            self.requires("pthreads4w/[^3]")

    def build_requirements(self):
        if self.settings.compiler != "msvc":
            self.tool_requires("m4/[^1.4]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "MPFR_", "mpfr_")

    def generate(self):
        if self.settings.compiler == "msvc":
            tc = CMakeToolchain(self)
            tc.cache_variables["BUILD_TESTING"] = False
            tc.cache_variables["BUILD_DOCS"] = False
            tc.cache_variables["MEMORY_MANAGER"] = self.options.memory_manager
            tc.cache_variables["WITH_NTL"] = False
            tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_CBLAS"] = not self.options.with_blas
            tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_CBLAS"] = self.options.with_blas
            # IPO/LTO breaks clang builds
            tc.cache_variables["IPO_SUPPORTED"] = False
            # handle run in a cross-build
            if cross_building(self):
                tc.cache_variables["FLINT_USES_POPCNT_EXITCODE"] = "1"
                tc.cache_variables["FLINT_USES_POPCNT_EXITCODE__TRYRUN_OUTPUT"] = ""
            tc.generate()

            deps = CMakeDeps(self)
            if Version(self.version) <= "3.0.1":
                deps.set_property("pthreads4w", "cmake_file_name", "PThreads")
            else:
                # https://github.com/flintlib/flint/commit/c6cc1078cb55903b0853fb1b6dc660887842dadf
                deps.set_property("pthreads4w", "cmake_file_name", "PThreads4W")
            deps.set_property("pthreads4w", "cmake_target_name", "PThreads4W::PThreads4W")
            deps.generate()
        else:
            VirtualBuildEnv(self).generate()
            if not cross_building(self):
                VirtualRunEnv(self).generate(scope="build")
            def yes_no(v): return "yes" if v else "no"
            tc = AutotoolsToolchain(self)
            tc.configure_args.append(f'--with-gmp={unix_path(self, self.dependencies["gmp"].package_folder)}')
            tc.configure_args.append(f'--with-mpfr={unix_path(self, self.dependencies["mpfr"].package_folder)}')
            tc.configure_args.append(f"--with-blas={yes_no(self.options.with_blas)}")
            if self.options.memory_manager == "gc":
                tc.configure_args.append(f"--with-gc={unix_path(self, self.dependencies["bdwgc"].package_folder)}")
                tc.configure_args.append("--disable-thread-safe")
            else:
                tc.configure_args.append(f"--enable-thread-safe={yes_no(self.options.memory_manager == 'reentrant')}")
                tc.configure_args.append("--without-gc")
            tc.configure_args.append("--without-ntl")
            tc.generate()
            tc = AutotoolsDeps(self)
            tc.generate()

    def build(self):
        if self.settings.compiler == "msvc":
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        if self.settings.compiler == "msvc":
            cmake = CMake(self)
            cmake.install()
        else:
            autotools = Autotools(self)
            autotools.install()
            fix_apple_shared_install_name(self)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))


    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "flint")
        self.cpp_info.set_property("cmake_file_name", "libflint")
        self.cpp_info.set_property("cmake_target_name", "libflint::libflint")

        self.cpp_info.libs = ["flint"]
        self.cpp_info.includedirs.append("include/flint")
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["pthread", "m"]
