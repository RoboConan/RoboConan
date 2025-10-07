import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime

required_conan_version = ">=2.1"


class RocksDBConan(ConanFile):
    name = "rocksdb"
    description = "A library that provides an embeddable, persistent key-value store for fast storage"
    license = "Apache-2.0 OR GPL-2.0-only"
    homepage = "https://github.com/facebook/rocksdb"
    topics = ("database", "leveldb", "facebook", "key-value")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_gflags": [True, False],
        "with_jemalloc": [True, False],
        "with_liburing": [True, False],
        "with_lz4": [True, False],
        "with_snappy": [True, False],
        "with_tbb": [True, False],
        "with_zlib": [True, False],
        "with_zstd": [True, False],
        "with_folly": [True, False],
        "enable_sse": [False, "sse42", "avx2"],
        "use_rtti": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_snappy": False,
        "with_gflags": False,
        "with_jemalloc": False,
        "with_liburing": False,
        "with_lz4": False,
        "with_tbb": True,
        "with_zlib": False,
        "with_zstd": False,
        "with_folly": False,
        "enable_sse": False,
        "use_rtti": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.with_liburing
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.enable_sse
        if self.settings.arch != "x86_64":
            del self.options.with_tbb
        if self.settings.build_type == "Debug":
            self.options.use_rtti = True  # Rtti are used in asserts for debug mode...

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_gflags:
            self.requires("gflags/[^2.2.2]")
        if self.options.with_snappy:
            self.requires("snappy/[^1.1.9]")
        if self.options.get_safe("with_liburing"):
            self.requires("liburing/[^2.7]")
        if self.options.with_lz4:
            self.requires("lz4/[^1.9.4]")
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_zstd:
            self.requires("zstd/[~1.5]")
        if self.options.get_safe("with_tbb"):
            self.requires("onetbb/[>=2021]")
        if self.options.with_jemalloc:
            self.requires("jemalloc/[^5.3.0]")
        if self.options.with_folly:
            self.requires("folly/[*]")

    def validate(self):
        check_min_cppstd(self, 17)

        if self.settings.arch not in ["x86_64", "ppc64le", "ppc64", "mips64", "armv8", "riscv64"]:
            raise ConanInvalidConfiguration("Rocksdb requires a 64-bit architecture.")

        if self.options.shared and self.options.with_folly:
            # https://github.com/facebook/rocksdb/blob/v10.5.1/CMakeLists.txt#L603
            raise ConanInvalidConfiguration(f"{self.ref} does not support a shared build with folly")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        replace_in_file(self, "CMakeLists.txt", "find_package(uring)", "find_package(uring REQUIRED CONFIG)")
        replace_in_file(self, "CMakeLists.txt", 'set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,--copy-dt-needed-entries")', "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["FAIL_ON_WARNINGS"] = False
        tc.variables["WITH_TESTS"] = False
        tc.variables["WITH_TOOLS"] = False
        tc.variables["WITH_CORE_TOOLS"] = False
        tc.variables["WITH_BENCHMARK_TOOLS"] = False
        tc.variables["USE_FOLLY"] = self.options.with_folly
        tc.variables["WITH_MD_LIBRARY"] = not is_msvc_static_runtime(self)
        tc.variables["ROCKSDB_INSTALL_ON_WINDOWS"] = self.settings.os == "Windows"
        tc.variables["WITH_GFLAGS"] = self.options.with_gflags
        tc.variables["WITH_SNAPPY"] = self.options.with_snappy
        tc.variables["WITH_LIBURING"] = self.options.get_safe("with_liburing", False)
        tc.variables["WITH_LZ4"] = self.options.with_lz4
        tc.variables["WITH_ZLIB"] = self.options.with_zlib
        tc.variables["WITH_ZSTD"] = self.options.with_zstd
        tc.variables["WITH_TBB"] = self.options.get_safe("with_tbb", False)
        tc.variables["WITH_JEMALLOC"] = self.options.with_jemalloc
        tc.variables["ROCKSDB_BUILD_SHARED"] = self.options.shared
        tc.variables["ROCKSDB_LIBRARY_EXPORTS"] = self.settings.os == "Windows" and self.options.shared
        tc.variables["ROCKSDB_DLL" ] = self.settings.os == "Windows" and self.options.shared
        tc.variables["USE_RTTI"] = self.options.use_rtti
        if not bool(self.options.get_safe("enable_sse")):
            tc.variables["PORTABLE"] = True
            tc.variables["FORCE_SSE42"] = False
        elif self.options.get_safe("enable_sse") == "sse42":
            tc.variables["PORTABLE"] = True
            tc.variables["FORCE_SSE42"] = True
        elif self.options.get_safe("enable_sse") == "avx2":
            tc.variables["PORTABLE"] = False
            tc.variables["FORCE_SSE42"] = False
        # not available yet in CCI
        tc.variables["WITH_NUMA"] = False
        tc.generate()

        deps = CMakeDeps(self)
        if self.options.with_jemalloc:
            deps.set_property("jemalloc", "cmake_file_name", "JeMalloc")
            deps.set_property("jemalloc", "cmake_target_name", "JeMalloc::JeMalloc")
        if self.options.get_safe("with_liburing"):
            deps.set_property("liburing", "cmake_file_name", "uring")
            deps.set_property("liburing", "cmake_target_name", "uring::uring")
        if self.options.with_zstd:
            deps.set_property("zstd", "cmake_target_name", "zstd::zstd")
        if self.options.with_folly:
            deps.set_property("folly", "cmake_additional_variables_prefixes", ["FOLLY"])
        if self.options.get_safe("with_tbb"):
            deps.set_property("onetbb", "cmake_target_name", "TBB::TBB")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _remove_static_libraries(self):
        rm(self, "rocksdb.lib", os.path.join(self.package_folder, "lib"))
        for lib in glob.glob(os.path.join(self.package_folder, "lib", "*.a")):
            if not lib.endswith(".dll.a"):
                os.remove(lib)

    def _remove_cpp_headers(self):
        for path in glob.glob(os.path.join(self.package_folder, "include", "rocksdb", "*")):
            if path != os.path.join(self.package_folder, "include", "rocksdb", "c.h"):
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        if self.options.shared:
            self._remove_static_libraries()
            self._remove_cpp_headers() # Force stable ABI for shared libraries
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        cmake_target = "rocksdb-shared" if self.options.shared else "rocksdb"
        self.cpp_info.set_property("cmake_file_name", "RocksDB")
        self.cpp_info.set_property("cmake_target_name", f"RocksDB::{cmake_target}")
        self.cpp_info.components["librocksdb"].libs = collect_libs(self)
        if self.settings.os == "Windows":
            self.cpp_info.components["librocksdb"].system_libs = ["shlwapi", "rpcrt4"]
            if self.options.shared:
                self.cpp_info.components["librocksdb"].defines = ["ROCKSDB_DLL"]
        elif self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["librocksdb"].system_libs = ["pthread", "m"]

        self.cpp_info.components["librocksdb"].set_property("cmake_target_name", f"RocksDB::{cmake_target}")
        if self.options.with_gflags:
            self.cpp_info.components["librocksdb"].requires.append("gflags::gflags")
        if self.options.with_snappy:
            self.cpp_info.components["librocksdb"].requires.append("snappy::snappy")
        if self.options.with_lz4:
            self.cpp_info.components["librocksdb"].requires.append("lz4::lz4")
        if self.options.with_zlib:
            self.cpp_info.components["librocksdb"].requires.append("zlib-ng::zlib-ng")
        if self.options.with_zstd:
            self.cpp_info.components["librocksdb"].requires.append("zstd::zstd")
        if self.options.get_safe("with_tbb"):
            self.cpp_info.components["librocksdb"].requires.append("onetbb::onetbb")
        if self.options.with_jemalloc:
            self.cpp_info.components["librocksdb"].requires.append("jemalloc::jemalloc")
        if self.options.with_folly:
            self.cpp_info.components["librocksdb"].requires.append("folly::folly")
