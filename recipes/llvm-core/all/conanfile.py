import json
import os
import re
import textwrap
from functools import cached_property
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.apple import is_apple_os
from conan.tools.build import check_min_cppstd, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.microsoft import is_msvc, msvc_runtime_flag
from conan.tools.scm import Version

required_conan_version = ">=2.26"


# Only the target matching the host-profile architecture is enabled by default in the recipe.
# Additional targets can be enabled by setting respective 'target_<target>' options to True.
# https://github.com/llvm/llvm-project/blob/llvmorg-20.1.3/llvm/CMakeLists.txt#L480-L510
LLVM_TARGETS = [
    "AArch64",
    "AMDGPU",
    "ARM",
    "AVR",
    "BPF",
    "Hexagon",
    "Lanai",
    "LoongArch",
    "Mips",
    "MSP430",
    "NVPTX",
    "PowerPC",
    "RISCV",
    "Sparc",
    "SPIRV",
    "SystemZ",
    "VE",
    "WebAssembly",
    "X86",
    "XCore"
]
EXPERIMENTAL_TARGETS = [
    "ARC",
    "CSKY",
    "DirectX",
    "M68k",
    "SPIRV",
    "Xtensa",
]


class LLVMCoreConan(ConanFile):
    name = "llvm-core"
    description = (
        "A toolkit for the construction of highly optimized compilers,"
        "optimizers, and runtime environments."
    )
    license = "Apache-2.0 WITH LLVM-exception"
    topics = ("llvm", "compiler")
    homepage = "https://llvm.org"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "monolithic": [True, False],
        "exceptions": [True, False],
        "rtti": [True, False],
        "threads": [True, False],
        "lto": ["On", "Off", "Full", "Thin"],
        "static_stdlib": [True, False],
        "unwind_tables": [True, False],
        "expensive_checks": [True, False],
        "use_perf": [True, False],
        "use_sanitizer": ["Address", "Memory", "MemoryWithOrigins", "Undefined", "Thread", "DataFlow", "Address;Undefined", "None"],
        "tools": [True, False],
        "utils": [True, False],
        "with_ffi": [True, False],
        "with_libedit": [True, False],
        "with_zlib": [True, False],
        "with_xml2": [True, False],
        "with_z3": [True, False],
        "with_zstd": [True, False],
    }
    options.update({f"target_{t}": [True, False] for t in LLVM_TARGETS + EXPERIMENTAL_TARGETS})
    default_options = {
        "shared": True,
        "fPIC": True,
        "monolithic": False,
        "exceptions": True,
        "rtti": True,
        "threads": True,
        "lto": "Off",
        "static_stdlib": False,
        "unwind_tables": True,
        "expensive_checks": False,
        "use_perf": False,
        "use_sanitizer": "None",
        "tools": True,
        "utils": True,
        "with_libedit": True,
        "with_ffi": False,
        "with_xml2": True,
        "with_z3": True,
        "with_zlib": True,
        "with_zstd": True,
    }
    default_options.update({f"target_{t}": False for t in LLVM_TARGETS + EXPERIMENTAL_TARGETS})
    options_description = {
        "monolithic": "Build a single monolithic shared library containing all LLVM components.",
    }

    no_copy_source = True

    @property
    def _host_target(self):
        arch = str(self.settings.arch)
        if arch in ["armv8|x86_64", "x86_64|armv8"]:
            return "AArch64;X86"
        if arch in ["armv8", "armv8.3", "arm64ec"]:
            return "AArch64"
        if arch.startswith("arm"):
            return "ARM"
        if arch.startswith("ppc"):
            return "PowerPC"
        if arch.startswith("xtensa"):
            return "Xtensa"
        return {
            "asm.js":  "WebAssembly",
            "avr":     "AVR",
            "mips":    "Mips",
            "mips64":  "Mips",
            "riscv32": "RISCV",
            "riscv64": "RISCV",
            "s390":    "SystemZ",
            "s390x":   "SystemZ",
            "sparc":   "Sparc",
            "sparcv9": "Sparc",
            "wasm":    "WebAssembly",
            "x86":     "X86",
            "x86_64":  "X86",
        }.get(arch)

    @property
    def _all_targets(self):
        targets = set(LLVM_TARGETS + EXPERIMENTAL_TARGETS)
        if Version(self.version) < 20:
            targets.remove("SPIRV")
        return targets

    @property
    def _targets_to_build(self):
        return ";".join(t for t in LLVM_TARGETS if self.options.get_safe(f"target_{t}"))

    @property
    def _experimental_targets_to_build(self):
        return ";".join(t for t in EXPERIMENTAL_TARGETS if self.options.get_safe(f"target_{t}"))

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        # Build only the host architecture and GPU targets by default.
        if self._host_target:
            setattr(self.options, f"target_{self._host_target}", True)
        self.options.target_AMDGPU = True
        self.options.target_NVPTX = True

        # Remove target options not supported by this version of LLVM.
        for target in set(LLVM_TARGETS + EXPERIMENTAL_TARGETS) - self._all_targets:
            self.options.rm_safe(f"target_{target}")

        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.with_libedit  # not supported on windows

        if is_apple_os(self):
            self.options["libxml2"].iconv = False

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        else:
            del self.options.monolithic

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_ffi:
            self.requires("libffi/[^3.4.4]")
        if self.options.get_safe("with_libedit"):
            self.requires("editline/[^3.1]")
        if self.options.with_zlib:
            self.requires("zlib-ng/[^2.0]")
        if self.options.with_xml2:
            self.requires("libxml2/[^2.12.5]")
        if self.options.with_z3:
            self.requires("z3/[^4.13.0]")
        if self.options.with_zstd:
            self.requires("zstd/[~1.5]")

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.20 <5]")
        self.tool_requires("ninja/[^1.10]")

    def validate(self):
        check_min_cppstd(self, 17)

        if self.options.shared:
            if is_apple_os(self) and self.options.with_xml2 and bool(self.dependencies["libxml2"].options.iconv):
                # FIXME iconv contains duplicate symbols in the libiconv and libcharset libraries (both of which are
                #  provided by libiconv). This may be an issue with how conan packages libiconv
                raise ConanInvalidConfiguration("iconv cannot be linked into the shared LLVM library on macos "
                                                "due to duplicate symbols. Use libxml2/*:iconv=False.")

        if self.options.exceptions and not self.options.rtti:
            raise ConanInvalidConfiguration("Cannot enable exceptions without rtti support")

    def validate_build(self):
        if os.getenv("CONAN_CENTER_BUILD_SERVICE") and self.settings.build_type == "Debug":
            if self.settings.os == "Linux":
                raise ConanInvalidConfiguration("Debug build is not supported on CCI due to resource limitations")
            elif self.options.shared:
                raise ConanInvalidConfiguration("Shared Debug build is not supported on CCI due to resource limitations")

    def source(self):
        sources = self.conan_data["sources"][self.version]
        get(self, **sources["llvm"], destination="llvm", strip_root=True)
        get(self, **sources["cmake"], destination="cmake", strip_root=True)
        apply_conandata_patches(self)
        modules_dir = Path("llvm", "cmake", "modules")
        for path in modules_dir.glob("Find*.cmake"):
            if path.name != "FindOCaml.cmake":
                path.unlink()
        modules_dir.joinpath("FindLibpfm.cmake").write_text("")

    def _apply_resource_limits(self, cmake_definitions):
        if os.getenv("CONAN_CENTER_BUILD_SERVICE"):
            self.output.info("Applying CCI Resource Limits")
            default_ram_per_compile_job = 16384
            default_ram_per_link_job = 2048
        else:
            default_ram_per_compile_job = None
            default_ram_per_link_job = None

        ram_per_compile_job = self.conf.get("user.llvm-core:ram_per_compile_job", default_ram_per_compile_job)
        if ram_per_compile_job:
            cmake_definitions["LLVM_RAM_PER_COMPILE_JOB"] = ram_per_compile_job

        ram_per_link_job = self.conf.get("user.llvm-core:ram_per_link_job", default_ram_per_link_job)
        if ram_per_link_job:
            cmake_definitions["LLVM_RAM_PER_LINK_JOB"] = ram_per_link_job

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        # https://releases.llvm.org/19.1.0/docs/CMake.html
        # Enables LLVM to find conan libraries during try_compile
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.cache_variables["LINKER_SUPPORTS_COLOR_DIAGNOSTICS"] = False  # breaks with mold

        # LLVM has two separate concepts of a "shared library build".
        # "BUILD_SHARED_LIBS" builds shared versions of all components instead of static.
        # "LLVM_BUILD_LLVM_DYLIB" links all static libraries into an additional monolithic LLVM shared library.
        # "LLVM_LINK_LLVM_DYLIB" uses the LLVM monolithic library when linking executables.
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared and not self.options.get_safe("monolithic")
        tc.cache_variables["LLVM_BUILD_LLVM_DYLIB"] = self.options.get_safe("monolithic", False)
        tc.cache_variables["LLVM_LINK_LLVM_DYLIB"] = self.options.get_safe("monolithic", False)
        tc.cache_variables["LLVM_ENABLE_PIC"] = self.options.get_safe("fPIC", True)

        tc.cache_variables["LLVM_BUILD_TOOLS"] = self.options.tools
        tc.cache_variables["LLVM_INCLUDE_TOOLS"] = self.options.tools
        tc.cache_variables["LLVM_INSTALL_TOOLS"] = self.options.tools

        tc.cache_variables["LLVM_BUILD_UTILS"] = self.options.utils
        tc.cache_variables["LLVM_INCLUDE_UTILS"] = self.options.utils
        tc.cache_variables["LLVM_INSTALL_UTILS"] = self.options.utils

        tc.cache_variables["LLVM_ABI_BREAKING_CHECKS"] = "WITH_ASSERTS"
        tc.cache_variables["LLVM_INCLUDE_BENCHMARKS"] = False
        tc.cache_variables["LLVM_INCLUDE_TOOLS"] = True
        tc.cache_variables["LLVM_INCLUDE_EXAMPLES"] = False
        tc.cache_variables["LLVM_INCLUDE_TESTS"] = False
        tc.cache_variables["LLVM_ENABLE_IDE"] = False
        tc.cache_variables["LLVM_ENABLE_EH"] = self.options.exceptions
        tc.cache_variables["LLVM_ENABLE_RTTI"] = self.options.rtti
        tc.cache_variables["LLVM_ENABLE_THREADS"] = self.options.threads
        tc.cache_variables["LLVM_ENABLE_LTO"] = self.options.lto
        tc.cache_variables["LLVM_STATIC_LINK_CXX_STDLIB"] = self.options.static_stdlib
        tc.cache_variables["LLVM_ENABLE_UNWIND_TABLES"] = self.options.unwind_tables
        tc.cache_variables["LLVM_ENABLE_EXPENSIVE_CHECKS"] = self.options.expensive_checks
        tc.cache_variables["LLVM_ENABLE_ASSERTIONS"] = str(self.settings.build_type) == "Debug"
        tc.cache_variables["LLVM_USE_PERF"] = self.options.use_perf
        tc.cache_variables["LLVM_ENABLE_LIBEDIT"] = self.options.get_safe("with_libedit", False)
        tc.cache_variables["LLVM_ENABLE_Z3_SOLVER"] = self.options.with_z3
        tc.cache_variables["LLVM_ENABLE_FFI"] = self.options.with_ffi
        tc.cache_variables["LLVM_ENABLE_ZLIB"] = "FORCE_ON" if self.options.with_zlib else False
        tc.cache_variables["LLVM_ENABLE_LIBXML2"] = "FORCE_ON" if self.options.with_xml2 else False
        tc.cache_variables["LLVM_ENABLE_ZSTD"] = "FORCE_ON" if self.options.with_zstd else False

        tc.cache_variables["LLVM_TARGETS_TO_BUILD"] = self._targets_to_build
        tc.cache_variables["LLVM_TARGET_ARCH"] = self._host_target

        # Bypass some checks in cmake/config-ix.cmake
        tc.cache_variables["HAVE_ZLIB"] = self.options.with_zlib
        tc.cache_variables["HAVE_LIBXML2"] = self.options.with_xml2
        tc.cache_variables["HAVE_ZSTD"] = self.options.get_safe("with_zstd", False)
        tc.cache_variables["HAVE_LIBEDIT"] = self.options.get_safe("with_libedit", False)
        tc.cache_variables["HAVE_CURL"] = False
        tc.cache_variables["HAVE_HTTPLIB"] = False
        tc.cache_variables["HAVE_BACKTRACE"] = False
        tc.cache_variables["HAVE_LIBPFM"] = False

        if is_msvc(self):
            build_type = str(self.settings.build_type).upper()
            tc.cache_variables[f"LLVM_USE_CRT_{build_type}"] = msvc_runtime_flag(self)

        if self.options.use_sanitizer != "None":
            tc.cache_variables["LLVM_USE_SANITIZER"] = self.options.use_sanitizer

        if self.settings.os == "Linux":
            # Workaround for: https://github.com/conan-io/conan/issues/13560
            tc.add_rpath_link = True

        if cross_building(self):
            from conan.tools.gnu import GnuToolchain
            gtc = GnuToolchain(self)
            gtc_vars = gtc.extra_env.vars(self)
            tc.cache_variables["LLVM_HOST_TRIPLE"] = gtc.triplets_info["host"]["triplet"]
            # The native build utilities don't need any external dependencies.
            tc.cache_variables["CROSS_TOOLCHAIN_FLAGS_NATIVE"] = ";".join([
                "-DLLVM_ENABLE_LIBEDIT=FALSE",
                "-DLLVM_ENABLE_Z3_SOLVER=FALSE",
                "-DLLVM_ENABLE_FFI=FALSE",
                "-DLLVM_ENABLE_ZLIB=FALSE",
                "-DLLVM_ENABLE_LIBXML2=FALSE",
                "-DLLVM_ENABLE_TERMINFO=FALSE",
            ])
            # CC/CXX env vars are used by LLVM to build native build tools
            env = Environment()
            env.define_path("CC", gtc_vars.get("CC_FOR_BUILD", "cc"))
            env.define_path("CXX", gtc_vars.get("CXX_FOR_BUILD", "c++"))
            env.vars(self).save_script("native_compiler_env")

        self._apply_resource_limits(tc.cache_variables)
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("editline", "cmake_file_name", "LibEdit")
        deps.set_property("editline", "cmake_target_name", "LibEdit::LibEdit")
        deps.generate()

    @property
    def _graphviz_file(self):
        return Path(self.build_folder) / f"{self.name}.dot"

    def _validate_components(self, components):
        direct_deps = {k.ref.name for k, v in self.dependencies.direct_host.items()}
        all_ext_deps = set()
        for component, info in components.items():
            if not component.startswith("LLVM"):
                raise ConanException(f"Unexpected component: {component}")
            for req in info["requires"]:
                if not req.startswith("LLVM"):
                    dep = req.split("::", 1)[0]
                    if dep not in direct_deps:
                        raise ConanException(f"Unexpected dependency for {component}: {req}")
                    all_ext_deps.add(dep)
        if direct_deps - all_ext_deps:
            raise ConanException(f"Dependencies not used by any components: {', '.join(direct_deps - all_ext_deps)}")

    @cached_property
    def _llvm_build_info(self):
        return {
            "components": components_from_dotfile(self._graphviz_file.read_text()),
        }

    @property
    def _build_info_file(self):
        return self._package_path / self._cmake_module_path / "conan_build_info.json"

    def _write_build_info(self, path):
        Path(path).write_text(json.dumps(self._llvm_build_info, indent=2))

    def _read_build_info(self) -> dict:
        return json.loads(self._build_info_file.read_text())

    def build(self):
        cmake = CMake(self)
        graphviz_args = [f"--graphviz={self._graphviz_file}"]

        # components not exported or not of interest
        exclude_patterns = [
            "LLVM.+_static",
            "LLVMTableGenGlobalISel.*",
            "CONAN_LIB.*",
            "LLVMExegesis.*",
            "LLVMCFIVerify.*",
            "-Wl,.*",
            r".*diaguids\.lib",  # https://github.com/llvm/llvm-project/issues/86250
        ]
        Path(self.build_folder, "CMakeGraphVizOptions.cmake").write_text(textwrap.dedent(f"""
            set(GRAPHVIZ_EXECUTABLES OFF)
            set(GRAPHVIZ_MODULE_LIBS OFF)
            set(GRAPHVIZ_OBJECT_LIBS OFF)
            set(GRAPHVIZ_IGNORE_TARGETS "{';'.join(exclude_patterns)}")
        """))
        cmake.configure(build_script_folder="llvm", cli_args=graphviz_args)
        self._write_build_info(self._build_info_file.name)
        self._validate_components(self._llvm_build_info["components"])
        cmake.build()

    @property
    def _package_path(self):
        return Path(self.package_folder)

    @property
    def _source_path(self):
        return Path(self.source_folder) / "llvm"

    @property
    def _cmake_module_path(self):
        return Path("lib") / "cmake" / "llvm"

    def package(self):
        copy(self, "LICENSE.TXT", self._source_path, self._package_path / "licenses")
        cmake = CMake(self)
        cmake.install()

        if self.options.get_safe("monolithic"):
            # Keep only libLLVM.so
            rm(self, "*.a", self._package_path / "lib")

        rm(self, "*.pdb", self._package_path / "lib")
        rm(self, "*.pdb", self._package_path / "bin")

        # Back up original cmake files for debugging purposes
        cmake_dir = self._package_path / "lib" / "cmake" / "llvm"
        copy(self, "*", cmake_dir, os.path.join(self.package_folder, "share", "conan", "llvm", "cmake_original"))

        # Remove CMake files that are handled by Conan
        rm(self, "LLVMConfigVersion.cmake", cmake_dir)
        rm(self, "LLVMExports*", cmake_dir)
        rm(self, "Find*", cmake_dir)
        # Rename *Config.cmake to not conflict with LLVMConfig.cmake generated Conan
        rename(self,
               cmake_dir / "LLVMConfig.cmake",
               cmake_dir / "LLVM-ConfigInternal.cmake")
        rename(self,
               cmake_dir / "LLVM-Config.cmake",
               cmake_dir / "LLVM-ConfigUtils.cmake")
        replace_in_file(self, cmake_dir / "AddLLVM.cmake",
                        "LLVM-Config",
                        "LLVM-ConfigUtils")

        # LLVM export utils as CMake targets. Add a helper .cmake file to reproduce this in Conan.
        bin_dir = Path(self.package_folder, "bin")
        save(self, cmake_dir / "conan_add_executable_targets.cmake",
            'get_filename_component(_IMPORT_PREFIX "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)\n\n'
            + "\n".join(
                f"if(NOT TARGET {x.stem})\n"
                f"  add_executable({x.stem} IMPORTED)\n"
                f'  set_target_properties({x.stem} PROPERTIES IMPORTED_LOCATION "${{_IMPORT_PREFIX}}/bin/{x.name}")\n'
                "endif()\n"
                for x in sorted(bin_dir.iterdir()) if x.suffix not in {".dll", ".pdb"}
            ),
        )

        self._write_build_info(self._build_info_file)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "LLVM")

        libs = collect_libs(self)
        components = self._read_build_info()["components"]
        for component_name, data in components.items():
            if component_name in libs:
                self.cpp_info.components[component_name].set_property("cmake_target_name", component_name)
                self.cpp_info.components[component_name].libs = [component_name]
                self.cpp_info.components[component_name].requires = data["requires"]
                self.cpp_info.components[component_name].system_libs = data["system_libs"]

        found_libs = set(collect_libs(self))
        component_libs = set(sum((c.libs for _, c in self.cpp_info.components.items()), []))
        if component_libs - found_libs:
            self.output.warning(f"Some component libraries were not found in lib/: {component_libs - found_libs}")
        if found_libs - component_libs:
            self.output.warning(f"Some libraries were not declared as components: {found_libs - component_libs}")

        self.cpp_info.set_property("cmake_build_modules", [
            self._cmake_module_path / "LLVM-ConfigInternal.cmake",
            self._cmake_module_path / "conan_add_executable_targets.cmake",
        ])
        self.cpp_info.components["LLVMSupport"].builddirs.append(self._cmake_module_path)


def parse_dotfile(dotfile, label_replacements=None):
    """
    Load the dependency graph defined by the nodes and edges in a dotfile.
    """
    label_replacements = label_replacements or {}
    labels = {}
    for node, label in re.findall(r'^\s*"(node\d+)"\s*\[\s*label\s*=\s*"(.+?)"', dotfile, re.MULTILINE):
        labels[node] = label_replacements.get(label, label)
    components = {l: [] for l in labels.values()}
    for src, dst in re.findall(r'^\s*"(node\d+)"\s*->\s*"(node\d+)"', dotfile, re.MULTILINE):
        components[labels[src]].append(labels[dst])
    return components


def components_from_dotfile(dotfile):
    """
    Parse the dotfile generated by the
    [cmake --graphviz](https://cmake.org/cmake/help/latest/module/CMakeGraphVizOptions.html)
    option to generate the list of available LLVM CMake targets and their inter-component dependencies.

    In future a [CPS](https://cps-org.github.io/cps/index.html) format could be used, or generated directly
    by the LLVM build system
    """
    label_replacements = {
        "-lpthread": "pthread",
        "LibEdit::LibEdit": "editline::editline",
        "LibXml2::LibXml2": "libxml2::libxml2",
        "z3::libz3": "z3::z3",
        "ZLIB::ZLIB": "zlib-ng::zlib-ng",
        "zstd::libzstd_shared": "zstd::zstd",
        "zstd::libzstd_static": "zstd::zstd",
    }
    known_system_libs = {
        "ole32",
        "delayimp",
        "shell32",
        "advapi32",
        "-delayload:shell32.dll",
        "uuid",
        "psapi",
        "-delayload:ole32.dll",
        "ntdll",
        "ws2_32",
        "rt",
        "m",
        "dl",
        "pthread"
    }
    components = {}
    for component, deps in parse_dotfile(dotfile, label_replacements).items():
        if component.startswith("LLVM"):
            components[component] = {
                "requires": [d for d in deps if d not in known_system_libs],
                "system_libs": [d for d in deps if d in known_system_libs],
            }
    return components
