import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class SymengineConan(ConanFile):
    name = "symengine"
    description = "A fast symbolic manipulation library, written in C++"
    license = "MIT"
    topics = ("symbolic", "algebra", "cas", "sympy")
    homepage = "https://symengine.org/"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "library"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "integer_class": ["boostmp", "gmp", "gmpxx", "flint"],
        "thread_safe": [True, False],
        "openmp": [True, False],
        "with_bfd": [True, False],
        "with_ecm": [True, False],
        "with_flint": [True, False],
        "with_mpc": [True, False],
        "with_mpfr": [True, False],
        "with_primesieve": [True, False],
        "with_tcmalloc": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "integer_class": "boostmp",  # using Boost by default for the more permissive license
        "thread_safe": False,
        "openmp": False,
        "with_bfd": False,
        "with_ecm": False,
        "with_flint": False,
        "with_mpc": False,
        "with_mpfr": False,
        "with_primesieve": False,
        "with_tcmalloc": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        copy(self, "conan_deps.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.options.openmp:
            self.options.thread_safe.value = True
        if self.options.integer_class == "flint" or self.options.with_mpc:
            self.options.with_flint.value = True
        if self.options.with_flint:
            self.options.with_mpfr.value = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 11)
        if self.options.integer_class == "boostmp" and self.options.with_mpfr:
            raise ConanInvalidConfiguration("integer_class=boostmp cannot be used with with_flint or with_mpfr")

    def requirements(self):
        # serialize-cereal.h
        self.requires("cereal/[^1.3]", transitive_headers=True, transitive_libs=True)
        if Version(self.version) >= "0.13.0":
            self.requires("fast_float/[<9]")
        if self.options.openmp:
            self.requires("openmp/system")
        if self.options.integer_class == "gmp":
            # cwrapper.h
            self.requires("gmp/[^6.3.0]", transitive_headers=True, transitive_libs=True)
        if self.options.integer_class == "boostmp":
            # mp_class.h:12
            self.requires("boost/[^1.71.0]", transitive_headers=True, libs=False)
        if self.options.with_bfd:
            self.requires("binutils/[^2.46]")
        if self.options.with_ecm:
            self.requires("gmp-ecm/[^7]", transitive_headers=True, transitive_libs=True)
        if self.options.with_flint:
            # flint_wrapper.h, eval_arb.h
            self.requires("flint/[>=2 <4]", transitive_headers=True)
        if self.options.with_mpc:
            # eval_mpc.h, eval.h
            self.requires("mpc/[^1.4]", transitive_headers=True)
        if self.options.with_mpfr:
            # eval_mpfr.h, cwrapper.h, eval.h
            self.requires("mpfr/[^4.2]", transitive_headers=True)
        if self.options.with_primesieve:
            self.requires("primesieve/[^12]")
        if self.options.with_tcmalloc:
            self.requires("gperftools/[^2]")

    def build_requirements(self):
        if self.options.with_bfd:
            self.tool_requires("binutils/<host_version>")

    def source(self):
        if "symforce" not in self.version:
            get(self, **self.conan_data["sources"][self.version], strip_root=True)
        else:
            get(self, **self.conan_data["sources"][self.version], strip_root=True,
                pattern="*/third_party/symengine/*", destination="..")
            move_folder_contents(self, "../third_party/symengine", self.source_folder)
        apply_conandata_patches(self)
        # Disable hardcoded C++11
        replace_in_file(self, "CMakeLists.txt", 'set(CMAKE_CXX_FLAGS "${CXX11_OPTIONS} ${CMAKE_CXX_FLAGS}")', '')
        # Let Conan choose fPIC
        replace_in_file(self, "CMakeLists.txt", 'set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${common}")', '')

        # Unvendor
        rm(self, "Find*.cmake", "cmake")
        replace_in_file(self, "CMakeLists.txt", "find_package(LINKH REQUIRED)", "")
        replace_in_file(self, "CMakeLists.txt", "find_package(EXECINFO REQUIRED)", "")
        rmdir(self, "symengine/utilities/cereal")
        rmdir(self, "symengine/utilities/fast_float")
        rmdir(self, "symengine/utilities/catch")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["BUILD_BENCHMARKS"] = False
        tc.cache_variables["INTEGER_CLASS"] = self.options.integer_class
        tc.cache_variables["MSVC_USE_MT"] = is_msvc_static_runtime(self)
        tc.cache_variables["WITH_OPENMP"] = self.options.openmp
        tc.cache_variables["WITH_SYMENGINE_THREAD_SAFE"] = self.options.thread_safe
        tc.cache_variables["WITH_SYSTEM_FASTFLOAT"] = True
        tc.cache_variables["WITH_SYSTEM_CEREAL"] = True
        tc.cache_variables["WITH_ARB"] = self.options.with_flint
        tc.cache_variables["WITH_BFD"] = self.options.with_bfd
        tc.cache_variables["WITH_ECM"] = self.options.with_ecm
        tc.cache_variables["WITH_FLINT"] = self.options.with_flint
        tc.cache_variables["WITH_LLVM"] = False
        tc.cache_variables["WITH_MPC"] = self.options.with_mpc
        tc.cache_variables["WITH_MPFR"] = self.options.with_mpfr
        tc.cache_variables["WITH_PIRANHA"] = False
        tc.cache_variables["WITH_PRIMESIEVE"] = self.options.with_primesieve
        tc.cache_variables["WITH_TCMALLOC"] = self.options.with_tcmalloc
        tc.cache_variables["ECM_TARGETS"] = "gmp-ecm::gmp-ecm"
        tc.cache_variables["GMP_TARGETS"] = "gmp::gmp"
        tc.cache_variables["BFD_TARGETS"] = "binutils::binutils"
        tc.cache_variables["PRIMESIEVE_TARGETS"] = "primesieve::primesieve"
        # For vendored teuchos on <= 0.14
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe("fPIC", True)
        if Version(self.version) < "0.14":
            tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5" # CMake 4 support
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("binutils", "cmake_file_name", "BFD")
        deps.set_property("cereal", "cmake_file_name", "CEREAL")
        deps.set_property("fast_float", "cmake_file_name", "FASTFLOAT")
        deps.set_property("flint", "cmake_file_name", "FLINT")
        deps.set_property("gmp", "cmake_file_name", "GMP")
        deps.set_property("gmp::gmpxx", "cmake_target_name", "gmpxx")
        deps.set_property("gmp::libgmp", "cmake_target_name", "gmp")
        deps.set_property("gmp-ecm", "cmake_file_name", "ECM")
        deps.set_property("gperftools", "cmake_file_name", "TCMALLOC")
        deps.set_property("mpc", "cmake_file_name", "MPC")
        deps.set_property("mpfr", "cmake_file_name", "MPFR")
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "CMake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SymEngine")
        self.cpp_info.set_property("cmake_target_name", "symengine")
        self.cpp_info.set_property("cmake_additional_variables_prefixes", ["SYMENGINE"])
        self.cpp_info.libs = ["symengine"]
        if "teuchos" in collect_libs(self):
            self.cpp_info.libs.append("teuchos")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]
