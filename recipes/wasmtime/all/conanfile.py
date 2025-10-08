import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import *
from conan.tools.layout import basic_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=2.1"


class WasmtimeConan(ConanFile):
    name = "wasmtime"
    description = "Standalone JIT-style runtime for WebAssembly, using Cranelift"
    license = "Apache-2.0"
    homepage = "https://github.com/bytecodealliance/wasmtime"
    topics = ("webassembly", "wasm", "wasi")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }
    no_copy_source = True

    @property
    def _sources_os_key(self):
        if is_msvc(self):
            return "Windows"
        elif self.settings.os == "Windows" and self.settings.compiler == "gcc":
            return "MinGW"
        return str(self.settings.os)

    def layout(self):
        basic_layout(self, src_folder="src")

    def configure(self):
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def package_id(self):
        del self.info.settings.compiler.version
        if self.info.settings.compiler == "clang":
            self.info.settings.compiler = "gcc"

    def validate(self):
        try:
            self.conan_data["sources"][self.version][self._sources_os_key][str(self.settings.arch)]
        except KeyError:
            raise ConanInvalidConfiguration("Binaries for this combination of architecture/version/os are not available")

        check_min_cppstd(self, 11)

    def build(self):
        # This is packaging binaries so the download needs to be in build
        get(self, **self.conan_data["sources"][self.version][self._sources_os_key][str(self.settings.arch)], strip_root=True)

    def package(self):
        copy(self, pattern="*.h", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.build_folder, "include"))
        copy(self, pattern="*.hh", dst=os.path.join(self.package_folder, "include"), src=os.path.join(self.build_folder, "include"))

        srclibdir = os.path.join(self.build_folder, "lib")
        dstlibdir = os.path.join(self.package_folder, "lib")
        dstbindir = os.path.join(self.package_folder, "bin")
        if self.options.shared:
            copy(self, "wasmtime.dll.lib", dst=dstlibdir, src=srclibdir, keep_path=False)
            copy(self, "wasmtime.dll", dst=dstbindir, src=srclibdir, keep_path=False)
            copy(self, "libwasmtime.dll.a", dst=dstlibdir, src=srclibdir, keep_path=False)
            copy(self, "libwasmtime.so*", dst=dstlibdir, src=srclibdir, keep_path=False)
            copy(self, "libwasmtime.dylib",  dst=dstlibdir, src=srclibdir, keep_path=False)
        else:
            copy(self, "wasmtime.lib", dst=dstlibdir, src=srclibdir, keep_path=False)
            copy(self, "libwasmtime.a", dst=dstlibdir, src=srclibdir, keep_path=False)

        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.build_folder)

    def package_info(self):
        if self.options.shared:
            if self.settings.os == "Windows":
                self.cpp_info.libs = ["wasmtime.dll"]
            else:
                self.cpp_info.libs = ["wasmtime"]
        else:
            if self.settings.os == "Windows":
                self.cpp_info.defines = ["WASM_API_EXTERN=", "WASI_API_EXTERN="]
            self.cpp_info.libs = ["wasmtime"]

        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "bcrypt", "advapi32", "userenv", "ntdll", "shell32", "ole32"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["pthread", "dl", "m", "rt"]
