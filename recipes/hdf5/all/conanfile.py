import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building, check_min_cppstd, valid_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class Hdf5Conan(ConanFile):
    name = "hdf5"
    description = "HDF5 is a data model, library, and file format for storing and managing data."
    license = "BSD-3-Clause"
    topics = "hdf", "data"
    homepage = "https://www.hdfgroup.org/solutions/hdf5/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_cxx": [True, False],
        "hl": [True, False],
        "threadsafe": [True, False],
        "with_zlib": [True, False],
        "szip_support": [None, "with_libaec", "with_szip"],
        "szip_encoding": [True, False],
        "parallel": [True, False],
        "enable_unsupported": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_cxx": True,
        "hl": True,
        "threadsafe": False,
        "with_zlib": True,
        "szip_support": None,
        "szip_encoding": False,
        "parallel": False,
        "enable_unsupported": False
    }

    @property
    def _min_cppstd(self):
        if Version(self.version) < "1.14.0":
            return "98"
        return "11"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.enable_cxx:
            self.settings.rm_safe("compiler.cppstd")
            self.settings.rm_safe("compiler.libcxx")
        if (not self.options.enable_unsupported and (self.options.enable_cxx or self.options.hl))\
            or (self.settings.os == "Windows" and not self.options.shared):
            del self.options.threadsafe
        if not bool(self.options.szip_support):
            del self.options.szip_encoding

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.szip_support == "with_libaec":
            self.requires("libaec/1.0.6")
        elif self.options.szip_support == "with_szip":
            self.requires("szip/[^2.1.1]")
        if self.options.parallel:
            self.requires("openmpi/[^4.1.0]")

    def validate(self):
        if self.options.parallel and not self.options.enable_unsupported:
            if self.options.enable_cxx:
                raise ConanInvalidConfiguration("Parallel and C++ options are mutually exclusive, forcefully allow with enable_unsupported=True")
            if self.options.get_safe("threadsafe", False):
                raise ConanInvalidConfiguration("Parallel and Threadsafe options are mutually exclusive, forcefully allow with enable_unsupported=True")
        if self.options.szip_support == "with_szip" and \
                self.options.szip_encoding and \
                not self.dependencies["szip"].options.enable_encoding:
            raise ConanInvalidConfiguration("encoding must be enabled in szip dependency (szip:enable_encoding=True)")
        if self.options.enable_cxx:
            check_min_cppstd(self, self._min_cppstd)

    def validate_build(self):
        if cross_building(self) and Version(self.version) < "1.14.4.3":
            # While building it runs some executables like H5detect
            raise ConanInvalidConfiguration("Current recipe doesn't support cross-building (yet)")

    def build_requirements(self):
        if Version(self.version) >= "1.14.0":
            self.tool_requires("cmake/[>=3.18 <5]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "set (CMAKE_POSITION_INDEPENDENT_CODE ON)", "")

    def generate(self):
        cmakedeps = CMakeDeps(self)
        cmakedeps.generate()

        tc = CMakeToolchain(self)
        if self.options.szip_support == "with_libaec":
            tc.variables["USE_LIBAEC"] = True
        tc.variables["HDF5_EXTERNALLY_CONFIGURED"] = True
        tc.variables["HDF5_EXTERNAL_LIB_PREFIX"] = ""
        tc.variables["HDF5_USE_FOLDERS"] = False
        tc.variables["HDF5_NO_PACKAGES"] = True
        tc.variables["ALLOW_UNSUPPORTED"] = False
        if Version(self.version) >= "1.10.6":
            tc.variables["ONLY_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["BUILD_STATIC_EXECS"] = False
        tc.variables["HDF5_ENABLE_COVERAGE"] = False
        tc.variables["HDF5_ENABLE_USING_MEMCHECKER"] = False
        if Version(self.version) >= "1.10.0":
            tc.variables["HDF5_MEMORY_ALLOC_SANITY_CHECK"] = False
        if Version(self.version) >= "1.10.5":
            tc.variables["HDF5_ENABLE_PREADWRITE"] = True
        tc.variables["HDF5_ENABLE_DEPRECATED_SYMBOLS"] = True
        tc.variables["HDF5_BUILD_GENERATORS"] = False
        tc.variables["HDF5_ENABLE_TRACE"] = False
        if self.settings.build_type == "Debug":
            tc.variables["HDF5_ENABLE_INSTRUMENT"] = False  # Option?
        tc.variables["HDF5_ENABLE_PARALLEL"] = self.options.parallel
        tc.variables["HDF5_ENABLE_Z_LIB_SUPPORT"] = self.options.with_zlib
        tc.variables["HDF5_ENABLE_SZIP_SUPPORT"] = bool(self.options.szip_support)
        tc.variables["HDF5_ENABLE_SZIP_ENCODING"] = self.options.get_safe("szip_encoding", False)
        tc.variables["HDF5_USE_ZLIB_NG"] = not self.dependencies["zlib-ng"].options.zlib_compat
        tc.variables["HDF5_PACKAGE_EXTLIBS"] = False
        tc.variables["HDF5_ENABLE_THREADSAFE"] = self.options.get_safe("threadsafe", False)
        tc.variables["HDF5_ENABLE_DEBUG_APIS"] = False # Option?
        tc.variables["BUILD_TESTING"] = False

        tc.variables["HDF5_INSTALL_INCLUDE_DIR"] = "include/hdf5"

        tc.variables["HDF5_BUILD_TOOLS"] = False
        tc.variables["HDF5_BUILD_EXAMPLES"] = False
        tc.variables["HDF5_BUILD_HL_LIB"] = self.options.hl
        tc.variables["HDF5_BUILD_FORTRAN"] = False
        tc.variables["HDF5_BUILD_CPP_LIB"] = self.options.enable_cxx
        if Version(self.version) >= "1.10.0":
            tc.variables["HDF5_BUILD_JAVA"] = False
        tc.variables["ALLOW_UNSUPPORTED"] = self.options.enable_unsupported
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _create_cmake_module_variables(self):
        module_file = os.path.join(self.package_folder, self._module_variables_file_rel_path)
        is_parallel = self.options.get_safe("parallel", False)
        content = "set(HDF5_IS_PARALLEL {})".format("ON" if is_parallel else "OFF")
        save(self, module_file, content)

    @property
    def _module_variables_file_rel_path(self):
        return os.path.join("lib", "cmake",  f"conan-official-{self.name}-variables.cmake")

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "libhdf5.settings", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

        # remove extra libs... building 1.8.21 as shared also outputs static libs on Linux.
        if self.options.shared:
            for lib in glob.glob(os.path.join(self.package_folder, "lib", "*.a")):
                if not lib.endswith(".dll.a"):
                    os.remove(lib)

        self._create_cmake_module_variables()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "HDF5")
        self.cpp_info.set_property("cmake_target_name", "HDF5::HDF5")
        self.cpp_info.set_property("pkg_config_name", "hdf5-all-do-not-use") # to avoid conflict with hdf5_c component
        self.cpp_info.set_property("cmake_build_modules", [self._module_variables_file_rel_path])

        def _config_libname(lib):
            if self.settings.os == "Windows" and self.settings.compiler != "gcc" and not self.options.shared:
                lib = "lib" + lib
            if self.settings.build_type == "Debug":
                debug_postfix = "_D" if self.settings.os == "Windows" else "_debug"
                return lib + debug_postfix
            # See config/cmake_ext_mod/HDFMacros.cmake
            return lib

        def add_component(component_name, lib_name=None, requires=None):
            component = self.cpp_info.components[component_name]
            lib_name = lib_name or component_name
            component.set_property("cmake_target_name", f"hdf5::{lib_name}")
            component.set_property("pkg_config_name", lib_name)
            component.libs = [_config_libname(lib_name)]
            component.requires = requires or []
            component.includedirs.append(os.path.join("include", "hdf5"))
            component.builddirs.append(os.path.join("lib", "cmake"))
            return component

        hdf5_c = add_component("hdf5_c", lib_name="hdf5")
        hdf5_c.includedirs.append(os.path.join("include", "hdf5"))

        if self.settings.os in ["Linux", "FreeBSD"]:
            hdf5_c.system_libs.extend(["dl", "m"])
            if self.options.get_safe("threadsafe"):
                hdf5_c.system_libs.append("pthread")
        elif self.settings.os == "Windows":
            hdf5_c.system_libs.append("Shlwapi")

        if self.options.shared:
            hdf5_c.defines.append("H5_BUILT_AS_DYNAMIC_LIB")

        if self.options.with_zlib:
            hdf5_c.requires.append("zlib-ng::zlib-ng")
        if self.options.szip_support == "with_libaec":
            hdf5_c.requires.append("libaec::libaec")
        elif self.options.szip_support == "with_szip":
            hdf5_c.requires.append("szip::szip")
        if self.options.parallel:
            hdf5_c.requires.append("openmpi::openmpi")

        if self.options.get_safe("enable_cxx"):
            add_component("hdf5_cpp", requires=["hdf5_c"])
        if self.options.get_safe("hl"):
            add_component("hdf5_hl", requires=["hdf5_c"])
            if self.options.get_safe("enable_cxx"):
                add_component("hdf5_hl_cpp", requires=["hdf5_c", "hdf5_cpp", "hdf5_hl"])
