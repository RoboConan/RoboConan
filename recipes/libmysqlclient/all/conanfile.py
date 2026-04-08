import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, cross_building, stdcpp_library, can_run
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime

required_conan_version = ">=2.1"


class LibMysqlClientCConan(ConanFile):
    name = "libmysqlclient"
    description = "A MySQL client library for C development."
    license = "GPL-2.0"
    topics = ("mysql", "sql", "connector", "database")
    homepage = "https://dev.mysql.com/downloads/mysql/"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_boost": [True, False],
        "with_curl": [True, False],
        "with_kerberos": [True, False],
        "with_ldap": [True, False],
        "with_protobuf": [True, False],
        "with_sasl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_curl": True,
        "with_boost": False,
        "with_kerberos": False,
        "with_ldap": False,
        "with_protobuf": True,
        "with_sasl": False,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Required
        self.requires("openssl/[>=1.1 <4]")
        if self.settings.os == "FreeBSD":
            self.requires("libunwind/[^1.8.1]")
        # Dependencies that would otherwise be bundled
        self.requires("icu/[*]")
        self.requires("editline/[^3.1]")
        self.requires("libevent/[^2.1.12]")
        self.requires("lz4/[^1.9.4]")
        self.requires("rapidjson/[>=0.0+git.20250205]")
        self.requires("zlib-ng/[^2.0]")
        self.requires("zstd/[~1.5]")
        # Optional deps
        if self.options.with_boost:
            # Requires an exact version of boost
            self.requires("boost/[<=1.77.0]", libs=False)
        if self.options.with_sasl:
            self.requires("cyrus-sasl/[^2.1.28]")
        if self.options.with_curl:
            self.requires("libcurl/[>=7.78 <9]")
        if self.options.with_kerberos:
            self.requires("krb5/[^1.21.2]")
        if self.options.with_ldap:
            self.requires("openldap/[^2.6.7]")
        if self.options.with_protobuf:
            self.requires("protobuf/[>=3.21.12]")

    def validate_build(self):
        check_min_cppstd(self, 17)

    def validate(self):
        if self.options.with_sasl and not self.dependencies["cyrus-sasl"].options.with_gssapi:
            raise ConanInvalidConfiguration(f"{self.ref} requires cyrus-sasl with with_gssapi=True")

    def build_requirements(self):
        if is_apple_os(self):
            self.tool_requires("cmake/[>=3.18 <5]")
        if self.settings.os == "FreeBSD" and not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        if self.options.with_protobuf:
            self.tool_requires("protobuf/<host_version>")
        if not can_run(self):
            # Required for comp_err, comp_sql, etc. build executables.
            self.tool_requires(f"libmysqlclient/{self.version}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

        for folder in ["client", "man", "mysql-test", "libbinlogstandalone"]:
            save(self, os.path.join(self.source_folder, folder, "CMakeLists.txt"), "")
        rmdir(self, os.path.join(self.source_folder, "storage", "ndb"))

        # Inject editline from Conan
        replace_in_file(self, os.path.join(self.source_folder, "cmake", "readline.cmake"),
                        "MARK_AS_ADVANCED(EDITLINE_INCLUDE_DIR EDITLINE_LIBRARY)",
                        "find_package(EDITLINE REQUIRED CONFIG)")

        # Inject zstd from Conan
        replace_in_file(self, os.path.join(self.source_folder, "cmake", "zstd.cmake"),
                        "NAMES zstd",
                        f"NAMES zstd {self.dependencies['zstd'].cpp_info.aggregated_components().libs[0]}")

        # And do not merge OpenSSL libs into mysqlclient lib
        replace_in_file(self, os.path.join(self.source_folder, "cmake", "libutils.cmake"),
                        'IF(WIN32 AND ${TARGET} STREQUAL "mysqlclient")',
                        "if(0)")

        # Do not copy shared libs of dependencies to package folder
        deps_shared = ["KERBEROS", "SASL", "LDAP", "PROTOBUF"]
        for dep in deps_shared:
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            f"MYSQL_CHECK_{dep}_DLLS()", "")

        # patchelf is not needed since we are not copying the shared libs
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "IF(NOT PATCHELF_EXECUTABLE)", "if(0)")

        replace_in_file(self, os.path.join(self.source_folder, "cmake", "install_macros.cmake"),
                        "  INSTALL_DEBUG_SYMBOLS(",
                        "  # INSTALL_DEBUG_SYMBOLS(")

    def generate(self):
        if not cross_building(self):
            vrenv = VirtualRunEnv(self)
            vrenv.generate(scope="build")

        def root(pkg):
            return self.dependencies[pkg].package_folder.replace("\\", "/")

        tc = CMakeToolchain(self)
        # Not used anywhere in the CMakeLists
        tc.cache_variables["DISABLE_SHARED"] = not self.options.shared
        tc.cache_variables["STACK_DIRECTION"] = "-1"  # stack grows downwards, on very few platforms stack grows upwards
        tc.cache_variables["WITHOUT_SERVER"] = True
        tc.cache_variables["WITH_UNIT_TESTS"] = False
        tc.cache_variables["ENABLED_PROFILING"] = False
        tc.cache_variables["MYSQL_MAINTAINER_MODE"] = False
        tc.cache_variables["WIX_DIR"] = False
        # Disable additional Linux distro-specific compiler checks.
        # The recipe already checks for minimum versions of supported compilers.
        tc.cache_variables["FORCE_UNSUPPORTED_COMPILER"] = True
        tc.cache_variables["WITH_BOOST"] = root("boost") if self.options.with_boost else "bundled"
        tc.cache_variables["WITH_CURL"] = root("libcurl") if self.options.with_curl else "none"
        tc.cache_variables["WITH_EDITLINE"] = "system"
        tc.cache_variables["WITH_FIDO"] = "bundled" # Not available on CCI
        tc.cache_variables["WITH_ICU"] = root("icu")
        tc.cache_variables["WITH_KERBEROS"] = root("krb5") if self.options.with_kerberos else "none"
        tc.cache_variables["WITH_LDAP"] = root("openldap") if self.options.with_ldap else "none"
        tc.cache_variables["WITH_LIBEVENT"] = "system"
        tc.cache_variables["WITH_LZ4"] = "system"
        tc.cache_variables["WITH_PROTOBUF"] = "system" # Optionally disabled in _patch_sources()
        tc.cache_variables["WITH_SASL"] = root("cyrus-sasl") if self.options.with_sasl else "none"
        tc.cache_variables["WITH_SSL"] = root("openssl")
        tc.cache_variables["WITH_ZLIB"] = "system"
        tc.cache_variables["WITH_ZSTD"] = "system"
        tc.cache_variables["ZSTD_INCLUDE_DIR"] = self.dependencies["zstd"].cpp_info.aggregated_components().includedirs[0].replace("\\", "/")
        libevent = self.dependencies["libevent"].cpp_info.aggregated_components()
        tc.cache_variables["LIBEVENT_INCLUDE_PATH"] = libevent.includedir
        tc.cache_variables["LIBEVENT_LIB_PATHS"] = libevent.libdir
        tc.cache_variables["SYSTEM_RAPIDJSON_FOUND"] = 1
        tc.cache_variables["RAPIDJSON_INCLUDE_DIR"] = self.dependencies["rapidjson"].cpp_info.includedir.replace("\\", "/")
        if is_msvc(self):
            tc.cache_variables["WINDOWS_RUNTIME_MD"] = not is_msvc_static_runtime(self)
        # Remove to ensure reproducible build, this only affects docs generation
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("editline", "cmake_file_name", "EDITLINE")
        deps.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

    def _patch_sources(self):
        libs_to_remove = []
        # Rapidjson vars are set via CMakeToolchain
        libs_to_remove.append("rapidjson")
        # Disable unwanted dependencies entirely
        if not self.options.with_boost:
            libs_to_remove.append("boost")
        if not self.options.with_protobuf:
            libs_to_remove.append("protobuf")
        if not self.options.with_ldap:
            libs_to_remove.append("ldap")
        if not self.options.with_sasl:
            libs_to_remove.append("sasl")
        if not self.options.with_kerberos:
            libs_to_remove.append("kerberos")
        for lib in libs_to_remove:
            save(self, os.path.join(self.source_folder, "cmake", f"{lib}.cmake"), "")
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            f"MYSQL_CHECK_{lib.upper()}()\n",
                            "",
                            strict=False)
            replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                            f"WARN_MISSING_SYSTEM_{lib.upper()}({lib.upper()}_WARN_GIVEN)",
                            f"# WARN_MISSING_SYSTEM_{lib.upper()}({lib.upper()}_WARN_GIVEN)",
                            strict=False)

        if self.settings.os == "Macos":
            replace_in_file(self, os.path.join(self.source_folder, "libmysql", "CMakeLists.txt"),
                            "COMMAND libmysql_api_test",
                            f"COMMAND DYLD_LIBRARY_PATH={os.path.join(self.build_folder, 'library_output_directory')} {os.path.join(self.build_folder, 'runtime_output_directory', 'libmysql_api_test')}")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        mkdir(self, os.path.join(self.package_folder, "licenses"))
        rename(self, os.path.join(self.package_folder, "LICENSE"), os.path.join(self.package_folder, "licenses", "LICENSE"))
        rm(self, "README", self.package_folder)
        rm(self, "*.pdb", self.package_folder, recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "plugin"))
        rmdir(self, os.path.join(self.package_folder, "docs"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        if self.settings.os == "Windows":
            if self.options.shared:
                rename(self, os.path.join(self.package_folder, "lib", "libmysql.dll"),
                             os.path.join(self.package_folder, "bin", "libmysql.dll"))
                rm(self, "*mysqlclient.*", os.path.join(self.package_folder, "lib"))
            else:
                rm(self, "*.dll", os.path.join(self.package_folder, "lib"))
                rm(self, "*libmysql.*", os.path.join(self.package_folder, "lib"))
        else:
            if self.options.shared:
                rm(self, "*.a", os.path.join(self.package_folder, "lib"))
            else:
                rm(self, "*.dylib", os.path.join(self.package_folder, "lib"))
                rm(self, "*.so*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "mysqlclient")
        self.cpp_info.libs = ["libmysql" if self.settings.os == "Windows" and self.options.shared else "mysqlclient"]
        self.cpp_info.includedirs.append(os.path.join("include", "mysql"))
        if not self.options.shared:
            stdcpplib = stdcpp_library(self)
            if stdcpplib:
                self.cpp_info.system_libs.append(stdcpplib)
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs.append("m")
            if self.settings.os == "Linux":
                self.cpp_info.system_libs.append("resolv")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.extend(["dnsapi", "secur32"])

        # TODO: There is no official FindMySQL.cmake, but it's a common Find files in many projects
        #       do we want to support it in CMakeDeps?
