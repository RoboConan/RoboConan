import os
import re
import textwrap
from functools import cached_property

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMakeToolchain
from conan.tools.env import Environment
from conan.tools.files import replace_in_file, save
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.scm import Version

from .utils import cuda_supported_arch_ranges


class CudaToolchain:
    def __init__(self, conanfile: ConanFile, skip_arch_flags=False):
        self._conanfile = conanfile

        cuda_version = self._conanfile.settings.get_safe("cuda.version")
        if not cuda_version:
            raise ConanInvalidConfiguration("'cuda.version' setting must be defined, e.g. 'cuda.version=12.1'.")

        # Allow `del self.settings.cuda.architectures` for packages that only use the cuda/cudart API without building any device code.
        have_architectures = conanfile.settings.get_safe("cuda.architectures") is not None
        skip_arch_flags = skip_arch_flags or not have_architectures
        if have_architectures and not self.arch_flags:
            raise ConanInvalidConfiguration("No valid CUDA architectures found in 'cuda.architectures' setting. "
                                            "Please specify at least one architecture, e.g. 'cuda.architectures=70,75'.")

        self.cudaflags = []
        if not skip_arch_flags:
            self.cudaflags.extend(self.arch_flags)
        if "cudart" in self._conanfile.dependencies.host:
            runtime_type = "shared" if self._conanfile.dependencies.host["cudart"].options.shared else "static"
            # This exact format is required to match CMake internals
            # https://github.com/Kitware/CMake/blob/v4.1.1/Modules/CMakeDetermineCompilerId.cmake#L703
            self.cudaflags.extend(["-cudart", runtime_type])
        for pkg in ["cudart", "cuda-crt", "cuda-driver-stubs", "libcudacxx", "thrust", "cub"]:
            if pkg in self._conanfile.dependencies.host:
                pkg_info = self._conanfile.dependencies.host[pkg].cpp_info
                for path in pkg_info.libdirs:
                    if self._is_msvc:
                        self.cudaflags.append(f"/LIBPATH:{path}")
                    else:
                        self.cudaflags.append(f"-L{path}")
                for path in pkg_info.includedirs:
                    self.cudaflags.append(f"-I{path}")
        self.cudaflags.extend(self._conanfile.conf.get("user.tools.build:cudaflags", check_type=list, default=[]))
        self.extra_cudaflags = []

    @cached_property
    def _is_msvc(self):
        return self._conanfile.settings.compiler == "msvc"

    @cached_property
    def _is_visual_studio_generator(self):
        if not self._is_msvc:
            return False
        generator = self._conanfile.conf.get("tools.cmake.cmaketoolchain:generator")
        return generator is None or "Visual Studio" in generator

    @cached_property
    def _host_compiler(self):
        if self._is_msvc:
            return None
        return AutotoolsToolchain(self._conanfile).vars().get("CC", None)

    @cached_property
    def architectures(self):
        return str(self._conanfile.settings.cuda.architectures).strip().split(",")

    @cached_property
    def arch_flags(self):
        # https://docs.nvidia.com/cuda/cuda-compiler-driver-nvcc/#gpu-name-gpuname-arch

        cuda_major = int(Version(self._conanfile.settings.cuda.version).major.value)
        supported_arch_range = cuda_supported_arch_ranges[cuda_major]

        flags = []
        for arch in self.architectures:
            if arch in ["native", "all", "all-major"]:
                flags.append(f"-arch={arch}")
                continue
            virtual = True
            real = True
            if "-" in arch:
                arch, suffix = arch.split("-", 1)
                if suffix == "virtual":
                    real = False
                elif suffix == "real":
                    virtual = False
                else:
                    raise ConanInvalidConfiguration(f"Unknown CUDA architecture suffix: {suffix}")
            assert re.match(r"\d\d\d?[a-z]?", arch), f"Invalid CUDA architecture value: {arch}"

            # Validate architecture
            if int(arch) < supported_arch_range[0]:
                raise ConanInvalidConfiguration(f"CUDA architecture {arch} is no longer supported by CUDA {cuda_major}.")
            if supported_arch_range[1] is not None and int(arch) > supported_arch_range[1]:
                raise ConanInvalidConfiguration(f"CUDA architecture {arch} is not supported by CUDA {cuda_major}.")

            if real and virtual:
                flags.append(f"-gencode=arch=compute_{arch},code=[compute_{arch},sm_{arch}]")
            elif virtual:
                flags.append(f"-gencode=arch=compute_{arch},code=compute_{arch}")
            elif real:
                flags.append(f"-gencode=arch=compute_{arch},code=sm_{arch}")
        return flags

    def environment(self):
        env = Environment()
        flags_combined = self.cudaflags + self.extra_cudaflags
        flags = " ".join(f for f in flags_combined if not f.startswith("/LIBPATH")).strip()
        env.define("NVCC_APPEND_FLAGS", flags)
        if self._host_compiler:
            env.define_path("NVCC_CCBIN", self._host_compiler)
            # Initialize CMAKE_CUDA_COMPILER
            env.define_path("CUDAHOSTCXX", self._host_compiler)
        # Initialize CMAKE_CUDA_FLAGS.
        env.define("CUDAFLAGS", flags)
        # Initialize CMAKE_CUDA_ARCHITECTURES. Requires CMake >= 3.20.
        env.define("CUDAARCHS", ";".join(self.architectures))
        if self._is_msvc:
            # nvcc does not correctly propagate -LIBPATH or -Xlinker /LIBPATH to link.exe, so we need to pass them via an env var instead.
            env.append("LINK", " ".join(f for f in flags_combined if f.startswith("/LIBPATH:")), separator=" ")
        return env

    def generate(self, env=None, scope="build"):
        env = env or self.environment()
        env_vars = env.vars(self._conanfile, scope)
        env_vars.save_script("cuda_toolchain")
        if os.path.exists("conan_toolchain.cmake"):
            # There's a weird edge case where CMAKE_CUDA_FLAGS is not yet initialized from CUDAFLAGS,
            # but CUDA CompilerID detection looks for '-cudart shared` in CMAKE_CUDA_FLAGS.
            # Set CMAKE_CUDA_FLAGS via the toolchain as well to work around this.
            architectures = ";".join(self.architectures)
            extra = textwrap.dedent(f"""
                # Injected by CudaToolchain
                set(CMAKE_CUDA_FLAGS "${{CMAKE_CUDA_FLAGS}} $ENV{{CUDAFLAGS}}")
                if (NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
                    set(CMAKE_CUDA_ARCHITECTURES "{architectures}" CACHE STRING "CUDA architectures")
                endif()
            """)
            if "cudart" in self._conanfile.dependencies.host:
                cudart = "Shared" if self._conanfile.dependencies.host["cudart"].options.shared else "Static"
                extra += f"\nset(CMAKE_CUDA_RUNTIME_LIBRARY {cudart})\n"
            if self._is_visual_studio_generator:
                # Help MSVC find visual_studio_integration by extending CMAKE_GENERATOR_TOOLSET
                cmake_tc = CMakeToolchain(self._conanfile)
                vs_toolset = cmake_tc.blocks["generic_system"].context()["toolset"]
                cuda_toolset = "cuda=" + self._conanfile.dependencies.build["nvcc"].package_folder.replace("\\", "/")
                replace_in_file(self._conanfile, "conan_toolchain.cmake",
                                f'set(CMAKE_GENERATOR_TOOLSET "{vs_toolset}"',
                                f'set(CMAKE_GENERATOR_TOOLSET "{vs_toolset},{cuda_toolset}"')
                # https://github.com/conan-io/conan/issues/17289#issuecomment-3001221611
                build_type = self._conanfile.settings.get_safe("build_type", "Release")
                extra += textwrap.dedent(f"""
                    if (NOT DEFINED CMAKE_TRY_COMPILE_CONFIGURATION)
                        set(CMAKE_TRY_COMPILE_CONFIGURATION "{build_type}")
                    endif()
                """)
            save(self._conanfile, "conan_toolchain.cmake", extra, append=True)


def validate_settings(conanfile: ConanFile):
    CudaToolchain(conanfile)


__all__ = [
    "CudaToolchain",
    "validate_settings",
]
