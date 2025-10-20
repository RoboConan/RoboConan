import os
from functools import cached_property
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building, check_min_cppstd
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import *
from conan.tools.microsoft import check_min_vs, is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.1"


class GrpcConan(ConanFile):
    name = "grpc"
    description = "Google's RPC (remote procedure call) library and framework."
    license = "Apache-2.0"
    homepage = "https://github.com/grpc/grpc"
    topics = ("rpc",)

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "codegen": [True, False],
        "secure": [True, False],
        "csharp_ext": [True, False],
        "csharp_plugin": [True, False],
        "node_plugin": [True, False],
        "objective_c_plugin": [True, False],
        "php_plugin": [True, False],
        "python_plugin": [True, False],
        "ruby_plugin": [True, False],
        "otel_plugin": [True, False],
        "with_libsystemd": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "codegen": True,
        "secure": False,
        "csharp_ext": False,
        "csharp_plugin": False,
        "node_plugin": False,
        "objective_c_plugin": False,
        "php_plugin": False,
        "python_plugin": False,
        "ruby_plugin": False,
        "otel_plugin": False,
        "with_libsystemd": False,
    }

    @property
    def _grpc_plugin_template(self):
        return "grpc_plugin_template.cmake.in"

    def export(self):
        copy(self, f"target_info/grpc_{self.version}.yml", self.recipe_folder, self.export_folder)

    def export_sources(self):
        copy(self, "conan_cmake_project_include.cmake", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        copy(self, f"cmake/{self._grpc_plugin_template}", self.recipe_folder, os.path.join(self.export_sources_folder, "src"))
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.with_libsystemd

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
            self.options["protobuf"].shared = True
            if cross_building(self):
                self.options["grpc"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # abseil requires:
        #   transitive_headers=True because grpc headers include abseil headers
        #   transitive_libs=True because generated code (grpc_cpp_plugin) require symbols from abseil
        # Set transitive_libs=True for protobuf to make it available without
        # explicitly having to add requires and tool_requires for it.
        # Saves a lot of pain with version range mismatch issues between host and build.
        self.requires("abseil/[>=20240116.1]", transitive_headers=True, transitive_libs=True)
        self.requires("protobuf/[>=3.27.0]", transitive_headers=True, transitive_libs=True)
        self.requires("re2/[>=20220601]")
        self.requires("c-ares/[>=1.19.1 <2]")
        self.requires("openssl/[>=1.1 <4]")
        self.requires("zlib-ng/[^2.0]")
        if self.options.get_safe("with_libsystemd"):
            self.requires("libsystemd/[^255]")
        if self.options.get_safe("otel_plugin"):
            self.requires("opentelemetry-cpp/[^1.14.2]")

    def package_id(self):
        del self.info.options.secure

    def validate(self):
        check_min_vs(self, "190")
        if is_msvc(self) and self.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} shared not supported by Visual Studio")

        check_min_cppstd(self, 17 if Version(self.version) >= "1.70" else 14)

        if self.options.shared and not self.dependencies.host["protobuf"].options.shared:
            raise ConanInvalidConfiguration(
                "If built as shared protobuf must be shared as well. "
                "Please, use `protobuf/*:shared=True`.",
            )

        abseil_cppstd = self.dependencies.host["abseil"].info.settings.compiler.cppstd
        if abseil_cppstd != self.settings.compiler.cppstd:
            raise ConanInvalidConfiguration(f"grpc and abseil must be built with the same compiler.cppstd setting")

    def build_requirements(self):
        # cmake >=3.25 required to use `cmake -E env --modify` below
        self.tool_requires("cmake/[>=3.25 <5]")
        self.tool_requires("protobuf/<host_version>")
        if cross_building(self):
            # when cross compiling we need pre compiled grpc plugins for protoc
            self.tool_requires(f"grpc/{self.version}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Let Conan define CMAKE_MSVC_RUNTIME_LIBRARY
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"), "include(cmake/msvc_static_runtime.cmake)", "")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PROJECT_grpc_INCLUDE"] = "conan_cmake_project_include.cmake"
        tc.cache_variables["gRPC_BUILD_CODEGEN"] = self.options.codegen
        tc.cache_variables["gRPC_BUILD_CSHARP_EXT"] = self.options.csharp_ext
        tc.cache_variables["gRPC_BUILD_TESTS"] = False
        # We need the generated cmake/ files (bc they depend on the list of targets, which is dynamic)
        tc.cache_variables["gRPC_INSTALL"] = True
        tc.cache_variables["gRPC_BUILD_GRPC_CPP_PLUGIN"] = True
        tc.cache_variables["gRPC_BUILD_GRPC_CSHARP_PLUGIN"] = self.options.csharp_plugin
        tc.cache_variables["gRPC_BUILD_GRPC_NODE_PLUGIN"] = self.options.node_plugin
        tc.cache_variables["gRPC_BUILD_GRPC_OBJECTIVE_C_PLUGIN"] = self.options.objective_c_plugin
        tc.cache_variables["gRPC_BUILD_GRPC_PHP_PLUGIN"] = self.options.php_plugin
        tc.cache_variables["gRPC_BUILD_GRPC_PYTHON_PLUGIN"] = self.options.python_plugin
        tc.cache_variables["gRPC_BUILD_GRPC_RUBY_PLUGIN"] = self.options.ruby_plugin
        tc.cache_variables["gRPC_BUILD_GRPCPP_OTEL_PLUGIN"] = self.options.get_safe("otel_plugin", False)
        tc.cache_variables["gRPC_USE_SYSTEMD"] = self.options.get_safe("with_libsystemd", False)
        # tell grpc to use the find_package versions
        for dep in ["ZLIB", "CARES", "RE2", "SSL", "PROTOBUF", "ABSL", "OPENTELEMETRY"]:
            tc.cache_variables[f"gRPC_{dep}_PROVIDER"] = "package"
        # Never download unnecessary archives
        tc.cache_variables["gRPC_DOWNLOAD_ARCHIVES"] = False
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = True
        # workaround for: install TARGETS given no BUNDLE DESTINATION for MACOSX_BUNDLE executable
        tc.cache_variables["CMAKE_MACOSX_BUNDLE"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        if self.settings_build.os == "Macos":
            # On macOS if all the following are true:
            # - protoc from protobuf has shared library dependencies
            # - grpc_cpp_plugin has shared library deps (when crossbuilding)
            # - using `make` as the cmake generator
            # Make will run commands via `/bin/sh` which will strip all env vars that start with `DYLD*`
            # This workaround wraps the protoc command to be invoked by CMake with a modified environment
            # to bypass OSX restrictions.
            replace_in_file(self, cmakelists,
                            "COMMAND ${_gRPC_PROTOBUF_PROTOC_EXECUTABLE}",
                            'COMMAND ${CMAKE_COMMAND} -E env --modify "DYLD_LIBRARY_PATH=path_list_prepend:$ENV{DYLD_LIBRARY_PATH}" ${_gRPC_PROTOBUF_PROTOC_EXECUTABLE}')

        if self.settings.os == "Macos":
            # See https://github.com/grpc/grpc/issues/36654#issuecomment-2228569158
            save(self, cmakelists, (
                "\ntarget_link_options(upb_textformat_lib PRIVATE -Wl,-undefined,dynamic_lookup)"
                "\ntarget_link_options(upb_json_lib PRIVATE -Wl,-undefined,dynamic_lookup)"
            ), append=True)

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @cached_property
    def _target_info(self):
        path = Path(self.recipe_folder, "target_info", f"grpc_{self.version}.yml")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

        # Create one custom module file per executable in order to emulate
        # CMake executables imported targets of grpc plugins.
        for executable, plugin_info in self._target_info["plugins"].items():
            target = f"gRPC::{executable}"
            option_name = executable.replace("grpc_", "")
            if executable == "grpc_cpp_plugin" or self.options.get_safe(option_name):
                self._create_executable_module_file(target, executable)

    def _create_executable_module_file(self, target, executable):
        content = load(self, os.path.join(self.source_folder, "cmake", self._grpc_plugin_template))
        content = content.replace("@target_name@", target)
        content = content.replace("@executable_name@", executable)
        content = content.replace("@find_program_variable@", f"{executable.upper()}_PROGRAM")
        save(self, os.path.join(self.package_folder, self._module_path, f"{executable}.cmake"), content)

    @property
    def _module_path(self):
        return os.path.join("lib", "cmake", "conan_trick")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gRPC")
        self.cpp_info.resdirs = ["share"]

        system_libs = []
        if self.settings.os == "Windows":
            system_libs = ["crypt32", "ws2_32", "wsock32"]
        elif self.settings.os in ["Linux", "FreeBSD"]:
            system_libs = ["m", "pthread"]

        renames = {"grpc": "_grpc"}
        for name, info in self._target_info["targets"].items():
            if self.options.secure and name in ["grpc_unsecure", "grpc++_unsecure"]:
                continue
            if not self.options.codegen and name in ["grpc++_reflection", "grpcpp_channelz"]:
                continue
            component = self.cpp_info.components[renames.get(name, name)]
            component.set_property("cmake_target_name", f"gRPC::{name}")
            # actually only gpr, grpc, grpc_unsecure, grpc++ and grpc++_unsecure should have a .pc file
            component.set_property("pkg_config_name", name)
            component.libs = [name]
            component.requires = [renames.get(x, x) for x in info["deps"]]
            component.system_libs = system_libs
            if name in ["grpc", "grpc_unsecure", "grpc_authorization_provider"]:
                if is_apple_os(self):
                    component.frameworks = ["CoreFoundation"]
                if self.options.get_safe("with_libsystemd"):
                    component.requires.append("libsystemd::libsystemd")

        # Executable imported targets are added through custom CMake module files,
        # since conan generators don't know how to emulate these kind of targets.
        grpc_modules = []
        for executable, plugin_info in self._target_info["plugins"].items():
            option_name = executable.replace("grpc_", "")
            if executable == "grpc_cpp_plugin" or self.options.get_safe(option_name):
                grpc_modules.append(os.path.join(self._module_path, f"{executable}.cmake"))
        self.cpp_info.set_property("cmake_build_modules", grpc_modules)

        ssl_roots_file_path = os.path.join(self.package_folder, "share", "grpc", "roots.pem")
        self.runenv_info.define_path("GRPC_DEFAULT_SSL_ROOTS_FILE_PATH", ssl_roots_file_path)
