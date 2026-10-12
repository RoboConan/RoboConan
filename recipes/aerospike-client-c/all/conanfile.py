import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import *
from conan.tools.gnu.autotools import Autotools
from conan.tools.gnu.autotoolstoolchain import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.4"


class AerospikeConan(ConanFile):
    name = "aerospike-client-c"
    license = "Apache-2.0"
    description = "The Aerospike C client provides a C interface for interacting with the Aerospike Database."
    homepage = "https://github.com/aerospike/aerospike-client-c"
    topics = ("aerospike", "client", "database")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "event_library": ["libev", "libuv", "libevent", None]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "event_library": None,
    }
    implements = ["auto_shared_fpic"]
    languages = ["C"]

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("This recipe is not compatible with Windows")

    def requirements(self):
        self.requires("lua/[^5]", transitive_headers=True, transitive_libs=True)
        self.requires("openssl/[<5]", transitive_headers=True, transitive_libs=True)
        self.requires("zlib-ng/[^2.0]")
        if self.options.event_library == "libev":
            self.requires("libev/[^4.24]", transitive_headers=True, transitive_libs=True)
        elif self.options.event_library == "libuv":
            self.requires("libuv/[^1]", transitive_headers=True, transitive_libs=True)
        elif self.options.event_library == "libevent":
            self.requires("libevent/[>=2.1.8 <3]", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["root"], strip_root=True)
        get(self, **sources["common"], strip_root=True, destination=os.path.join("modules", "common"))
        get(self, **sources["mod-lua"], strip_root=True, destination=os.path.join("modules", "mod-lua"))
        replace_in_file(self, "Makefile", "CC_FLAGS = -std=gnu99 -g -Wall -fPIC -O$(O)", "CC_FLAGS = -std=gnu99 -Wall")
        replace_in_file(self, "Makefile", "LUA_OBJECTS = $(filter-out $(LUAMOD)/lua.o, $(shell ls $(LUAMOD)/*.o))", "")
        replace_in_file(self, os.path.join("modules", "mod-lua", "Makefile"), "MODULES += LUAMOD", "")
        replace_in_file(self, os.path.join("modules", "mod-lua", "project", "modules.mk"), "ifndef LUAMOD", "ifeq (0,1)")
        replace_in_file(self, os.path.join("modules", "mod-lua", "project", "modules.mk"), "ifeq ($(wildcard $(LUAMOD)/makefile),)", "ifeq (0,1)")

    def generate(self):
        tc = AutotoolsToolchain(self)
        for var, value in tc.vars().items():
            if var != "LDFLAGS":
                tc.make_args.append(f"{var}={value}")
        tc.make_args.append("TARGET_BASE=target")
        tc.make_args.append(f"LUAMOD={self.dependencies['lua'].cpp_info.includedir}")
        if self.options.event_library:
            tc.make_args.append(f"EVENT_LIB={self.options.event_library}")
        includedirs = []
        libdirs = []
        libs = []
        for dep in reversed(self.dependencies.host.topological_sort.values()):
            cpp_info = dep.cpp_info.aggregated_components()
            includedirs += cpp_info.includedirs
            libdirs += cpp_info.libdirs
            libs += cpp_info.libs
        include_flags = " ".join(f"-I{i}" for i in includedirs)
        libdir_flags = " ".join(f"-L{l}" for l in libdirs)
        lib_flags = " ".join(f"-l{l}" for l in libs)
        tc.make_args.append(f"EXT_CFLAGS={include_flags}" + (" -fPIC" if self.options.get_safe("fPIC", True) else ""))
        tc.make_args.append(f"LDFLAGS={tc.vars().get('LDFLAGS', '')} {libdir_flags} {lib_flags}")
        tc.generate()

    def build(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.make()

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*", os.path.join(self.source_folder, "target", "include"), os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "lib/*.so*", os.path.join(self.source_folder, "target"), self.package_folder)
            copy(self, "lib/*.dylib", os.path.join(self.source_folder, "target"), self.package_folder)
        else:
            copy(self, "lib/*.a", os.path.join(self.source_folder, "target"), self.package_folder)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["aerospike"]

        self.cpp_info.defines = []
        if self.options.event_library == "libev":
            self.cpp_info.defines.append("AS_USE_LIBEV")
        elif self.options.event_library == "libuv":
            self.cpp_info.defines.append("AS_USE_LIBUV")
        elif self.options.event_library == "libevent":
            self.cpp_info.defines.append("AS_USE_LIBEVENT")
