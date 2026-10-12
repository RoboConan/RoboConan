import os
from functools import cached_property
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import *
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class GoogleCloudCppConan(ConanFile):
    name = "google-cloud-cpp"
    description = "C++ Client Libraries for Google Cloud Services"
    license = "Apache-2.0"
    topics = (
        "google",
        "cloud",
        "google-cloud-storage",
        "google-cloud-platform",
        "google-cloud-pubsub",
        "google-cloud-spanner",
        "google-cloud-bigtable",
    )
    homepage = "https://github.com/googleapis/google-cloud-cpp"
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

    @cached_property
    def _components_data(self):
        path = Path(self.recipe_folder, "components", f"{self.version}.yml")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @property
    def _ga_components(self):
        return self._components_data["components"]

    @property
    def _proto_components(self):
        return self._components_data["proto_components"]

    @property
    def _proto_component_dependencies(self):
        return self._components_data["dependencies"]

    # Some components require custom dependency definitions.
    _REQUIRES_CUSTOM_DEPENDENCIES = {
        "bigquery", "bigtable", "iam", "oauth2", "pubsub", "spanner", "storage",
    }

    def export(self):
        copy(self, f"components/{self.version}.yml", self.recipe_folder, self.export_folder)

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
            self.options["protobuf"].shared = True
            self.options["grpc"].shared = True

    def validate(self):
        if is_msvc(self) and self.info.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} shared not supported by Visual Studio")

        check_min_cppstd(self, 14)

        if (self.info.options.shared and
                (not self.dependencies["protobuf"].options.shared
                 or not self.dependencies["grpc"].options.shared)):
            raise ConanInvalidConfiguration(
                "If built as shared, protobuf, and grpc must be shared as well."
                " Please, use `protobuf/*:shared=True`, and `grpc/*:shared=True`.")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        for path in [
            "google/cloud/internal/curl_handle.h",
            "google/cloud/internal/oauth2_credentials.h",
            "google/cloud/internal/rest_response.h",
            "google/cloud/storage/iam_policy.h",
            "google/cloud/storage/internal/hash_function_impl.h",
            "google/cloud/storage/internal/object_read_source.h",
            "google/cloud/pubsub/ack_handler.h",
        ]:
            header = Path(self.source_folder, path)
            header.write_text("#include <cstdint>\n" + header.read_text())

    def requirements(self):
        self.requires("grpc/[^1.50]", transitive_headers=True)
        self.requires("protobuf/[>=4.23]", transitive_headers=True)
        self.requires("abseil/[>=20230125.3]", transitive_headers=True)
        self.requires("nlohmann_json/[^3]")
        self.requires("crc32c/[^1.1.2]")
        self.requires("libcurl/[>=7.78 <9]")
        self.requires("openssl/[<5]")
        self.requires("zlib-ng/[^2.0]")

    def build_requirements(self):
        self.tool_requires("grpc/<host_version>")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["GOOGLE_CLOUD_CPP_WITH_MOCKS"] = False
        tc.variables["GOOGLE_CLOUD_CPP_ENABLE_MACOS_OPENSSL_CHECK"] = False
        tc.variables["GOOGLE_CLOUD_CPP_ENABLE_WERROR"] = False
        tc.variables["GOOGLE_CLOUD_CPP_ENABLE"] = ",".join(self._ga_components)
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0177"] = "NEW"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        # This was informed by comments in the grpc port. On macOS `Make` will
        # run commands via `/bin/sh`. `/bin/sh` is subject to System Integrity
        # Protections.  In particular, the system will purge the DYLD_LIBRARY_PATH
        # environment variables:
        #     https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/RuntimeProtections/RuntimeProtections.html
        if self.settings_build.os == "Macos":
            replace_in_file(self, os.path.join(self.source_folder, "cmake/CompileProtos.cmake"),
                            "${Protobuf_PROTOC_EXECUTABLE} ARGS",
                            '${CMAKE_COMMAND} -E env "DYLD_LIBRARY_PATH=$ENV{DYLD_LIBRARY_PATH}" ${Protobuf_PROTOC_EXECUTABLE} ARGS')

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, path=os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, path=os.path.join(self.package_folder, "lib", "pkgconfig"))

    def _add_proto_component(self, component):
        self.cpp_info.components[component].requires = self._proto_component_dependencies.get(component, [])
        self.cpp_info.components[component].libs = [f"google_cloud_cpp_{component}"]
        # https://github.com/googleapis/google-cloud-cpp/blob/v2.28.0/cmake/AddPkgConfig.cmake#L93
        self.cpp_info.components[component].set_property("pkg_config_name", f"google_cloud_cpp_{component}")

    def _add_grpc_component(self, component, protos, extra=None):
        SHARED_REQUIRES=["grpc_utils", "common", "grpc::grpc++", "grpc::_grpc", "protobuf::libprotobuf", "abseil::memory"]
        self.cpp_info.components[component].requires = (extra or []) + [protos] + SHARED_REQUIRES
        self.cpp_info.components[component].libs = [f"google_cloud_cpp_{component}"]
        self.cpp_info.components[component].set_property("pkg_config_name", f"google_cloud_cpp_{component}")

    # The compute libraries do not use gRPC, and they have many components
    # with dependencies between them
    def _add_compute_component(self, component, protos):
        SHARED_REQUIRES = ["rest_protobuf_internal", "rest_internal", "common"]
        # Common components shared by other compute components
        COMPUTE_COMMON_COMPONENTS = [
            "compute_global_operations",
            "compute_global_organization_operations",
            "compute_region_operations",
            "compute_zone_operations",
        ]
        requires = [protos]
        if component not in COMPUTE_COMMON_COMPONENTS:
            requires += COMPUTE_COMMON_COMPONENTS
        self.cpp_info.components[component].requires = requires + SHARED_REQUIRES
        self.cpp_info.components[component].libs = [f"google_cloud_cpp_{component}"]
        self.cpp_info.components[component].set_property("pkg_config_name", f"google_cloud_cpp_{component}")

    def package_info(self):
        self.cpp_info.components["common"].requires = ["abseil::any", "abseil::flat_hash_map", "abseil::memory", "abseil::optional", "abseil::time"]
        self.cpp_info.components["common"].libs = ["google_cloud_cpp_common"]
        self.cpp_info.components["common"].set_property("pkg_config_name", "google_cloud_cpp_common")

        self.cpp_info.components["rest_internal"].requires = ["common", "libcurl::libcurl", "openssl::ssl", "openssl::crypto", "zlib-ng::zlib-ng"]
        self.cpp_info.components["rest_internal"].libs = ["google_cloud_cpp_rest_internal"]
        self.cpp_info.components["rest_internal"].set_property("pkg_config_name", f"google_cloud_cpp_rest_internal")

        # A small number of gRPC-generated stubs are used directly in the common components
        # shared by all gRPC-based libraries.  These must be defined without reference to `grpc_utils`.
        GRPC_UTILS_REQUIRED_PROTOS = {
            "iam_credentials_v1_iamcredentials_protos",
            "iam_v1_policy_protos",
            "longrunning_operations_protos",
            "rpc_error_details_protos",
            "rpc_status_protos",
        }
        for component in GRPC_UTILS_REQUIRED_PROTOS:
            self._add_proto_component(component)

        self.cpp_info.components["grpc_utils"].requires = list(GRPC_UTILS_REQUIRED_PROTOS) + ["common", "abseil::function_ref", "abseil::memory", "abseil::time", "grpc::grpc++", "grpc::_grpc"]
        self.cpp_info.components["grpc_utils"].libs = ["google_cloud_cpp_grpc_utils"]
        self.cpp_info.components["grpc_utils"].set_property("pkg_config_name", "google_cloud_cpp_grpc_utils")

        for component in self._proto_components:
            if component == "storage_protos":
                # The `storage_protos` are compiled only when needed. They are
                # not used in Conan because they are only needed for an
                # experimental library, supporting an allow-listed service.
                continue
            if component not in GRPC_UTILS_REQUIRED_PROTOS:
                self._add_proto_component(component)

        # Interface libraries for backwards compatibility
        for old_name, new_name in [
            ("cloud_bigquery_protos", "bigquery_protos"),
            ("cloud_dialogflow_v2_protos", "dialogflow_es_protos"),
            ("cloud_speech_protos", "speech_protos"),
            ("cloud_texttospeech_protos", "texttospeech_protos"),
            ("devtools_cloudtrace_v2_trace_protos", "trace_protos"),
            ("devtools_cloudtrace_v2_tracing_protos", "trace_protos"),
            ("logging_type_type_protos", "logging_type_protos"),
        ]:
            self.cpp_info.components[old_name].requires = [new_name]
            self.cpp_info.components[old_name].set_property("pkg_config_name", f"google_cloud_cpp_{old_name}")

        for component in self._ga_components:
            protos=f"{component}_protos"
            # `compute` components do not depend on gRPC
            if component.startswith("compute_"):
                # Individual compute proto libraries were replaced with a single
                # `compute_protos` library.
                protos = "compute_protos"
                self._add_compute_component(component, protos)
                continue
            # `storage` is the only component that does not depend on a matching `*_protos` library
            if component in self._REQUIRES_CUSTOM_DEPENDENCIES:
                continue
            self._add_grpc_component(component, protos)

        self._add_grpc_component("bigtable", "bigtable_protos")
        self._add_grpc_component("iam", "iam_protos")
        self._add_grpc_component("pubsub", "pubsub_protos", ["abseil::flat_hash_map"])
        self._add_grpc_component("spanner", "spanner_protos",  ["abseil::fixed_array", "abseil::numeric", "abseil::strings", "abseil::time"])

        self.cpp_info.components["rest_protobuf_internal"].requires = ["rest_internal", "grpc_utils", "common"]
        self.cpp_info.components["rest_protobuf_internal"].libs = ["google_cloud_cpp_rest_protobuf_internal"]
        self.cpp_info.components["rest_protobuf_internal"].set_property("pkg_config_name", "google_cloud_cpp_rest_protobuf_internal")

        # The `google-cloud-cpp::compute` interface library groups all the compute
        # libraries in a single target.
        self.cpp_info.components["compute"].requires = [c for c in self._ga_components if c.startswith("compute_")]
        self.cpp_info.components["compute"].set_property("pkg_config_name", "google_cloud_cpp_compute")

        # The `google-cloud-cpp::oauth2` library does not depend on gRPC or any protos.
        self.cpp_info.components["oauth2"].requires = ["rest_internal", "common", "nlohmann_json::nlohmann_json", "libcurl::libcurl", "openssl::ssl", "openssl::crypto", "zlib-ng::zlib-ng"]
        self.cpp_info.components["oauth2"].libs = ["google_cloud_cpp_oauth2"]
        self.cpp_info.components["oauth2"].set_property("pkg_config_name", "google_cloud_cpp_oauth2")

        self.cpp_info.components["storage"].requires = ["rest_internal", "common", "nlohmann_json::nlohmann_json", "abseil::memory", "abseil::strings", "abseil::str_format", "abseil::time", "abseil::variant", "crc32c::crc32c", "libcurl::libcurl", "openssl::ssl", "openssl::crypto", "zlib-ng::zlib-ng"]
        self.cpp_info.components["storage"].libs = ["google_cloud_cpp_storage"]
        self.cpp_info.components["storage"].set_property("pkg_config_name", "google_cloud_cpp_storage")

        # Match googleapis.pc exported by the project
        # https://github.com/googleapis/google-cloud-cpp/blob/v2.28.0/external/googleapis/CMakeLists.txt#L398-L431
        self.cpp_info.components["googleapis"].set_property("pkg_config_name", "googleapis")
        self.cpp_info.components["googleapis"].requires = [
            "bigtable_protos",
            "cloud_bigquery_protos",
            "iam_protos",
            "pubsub_protos",
            # "storage_protos", - skipped in the recipe
            "logging_protos",
            "iam_v1_iam_policy_protos",
            "iam_v1_options_protos",
            "iam_v1_policy_protos",
            "longrunning_operations_protos",
            "api_auth_protos",
            "api_annotations_protos",
            "api_client_protos",
            "api_field_behavior_protos",
            "api_http_protos",
            "rpc_status_protos",
            "rpc_error_details_protos",
            "type_expr_protos",
            "grpc::grpc++",
            "grpc::_grpc",
            "openssl::openssl",
            "protobuf::libprotobuf",
            "zlib-ng::zlib-ng",
            # "c-ares::c-ares", - listed, but not actually used anywhere
        ]
