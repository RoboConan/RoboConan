import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv
from conan.tools.files import *
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.1"


class OpenUCXConan(ConanFile):
    name = "openucx"
    description = ("Unified Communication X (UCX) is an award winning, optimized "
                   "production proven-communication framework for modern, high-bandwidth "
                   "and low-latency networks.")
    license = "BSD-3-Clause"
    homepage = "http://www.openucx.org/"
    topics = ("networking", "hpc", "mpi", "gemini", "pgas", "rdma", "infiniband", "iwarp", "roce", "cray", "verbs", "shared-memory", "aries")
    package_type = "shared-library"  # static build fails with an internal linker error
    settings = "os", "arch", "compiler", "build_type", "cuda"
    options = {
        "bfd": [True, False],
        "cma": [True, False],
        "cuda": [True, False],
        "dc": [True, False],
        "devx": [True, False],
        "dm": [True, False],
        "fuse3": [True, False],
        "gdrcopy": [True, False],
        "ib_hw_tm": [True, False],
        "mad": [True, False],
        "mlx5": [True, False],
        "multithreading": [True, False],
        "openmp": [True, False],
        "rc": [True, False],
        "rdmacm": [True, False],
        "tuning": [True, False],
        "ud": [True, False],
        "verbs": [True, False],
        "xpmem": [True, False],
        "ze": [True, False],
    }
    default_options = {
        "bfd": True,
        "cma": False,
        "cuda": True,
        "dc": False,
        "devx": False,
        "dm": False,
        "fuse3": False,
        "gdrcopy": False,
        "ib_hw_tm": False,
        "mad": False,
        "mlx5": False,
        "multithreading": True,
        "openmp": True,
        "rc": False,
        "rdmacm": False,
        "tuning": False,
        "ud": False,
        "verbs": False,
        "xpmem": False,
        "ze": False,
    }
    options_description = {
        "bfd":            "Enable using BFD support for detailed backtrace",
        "cma":            "Enable Cross Memory Attach",
        "cuda":           "Enable the use of CUDA",
        "dc":             "Compile with IB Dynamic Connection support",
        "devx":           "Compile with DEVX support",
        "dm":             "Compile with Device Memory support",
        "fuse3":          "Enable the use of FUSEv3",
        "gdrcopy":        "Enable the use of gdrcopy for CUDA",
        "ib_hw_tm":       "Compile with IB Tag Matching support",
        "mad":            "Enable Infiniband MAD support",
        "mlx5":           "Compile with mlx5 Direct Verbs support",
        "multithreading": "Enable thread support in UCP and UCT",
        "openmp":         "Enable OpenMP support",
        "rc":             "Compile with IB Reliable Connection support",
        "rdmacm":         "Enable the use of RDMACM",
        "tuning":         "Enable parameter tuning in run-time",
        "ud":             "Compile with IB Unreliable Datagram support",
        "verbs":          "Build OpenFabrics support",
        "xpmem":          "Enable the use of Cray XPMEM",
        "ze":             "Enable the use of ZE (oneAPI Level Zero)",
        # "knem":           "Enable the use of KNEM",
        # "rocm":           "Enable the use of ROCm",
        # "ugni":           "Build Cray UGNI support",
    }
    implements = ["auto_shared_fpic"]

    python_requires = "conan-cuda/latest"
    python_requires_extend = "conan-cuda.Cuda"

    def layout(self):
        basic_layout(self, src_folder="src")

    def configure(self):
        if not self.options.cuda:
            del self.settings.cuda

    def package_id(self):
        if self.info.options.cuda:
            # No CUDA kernels are built by the project
            del self.info.settings.cuda

    def requirements(self):
        if any(self.options.get_safe(opt) for opt in ["mad", "mlx5", "rdmacm", "verbs"]):
            self.requires("rdma-core/[*]")
        if self.options.fuse3:
            self.requires("libfuse/[^3.10.5]")
        if self.options.gdrcopy:
            self.requires("gdrcopy/[^2.0]")
        if self.options.ze:
            self.requires("level-zero/[^1.17.39]")
        if self.options.openmp:
            self.requires("openmp/system")
        if self.options.cuda:
            self.cuda.requires("cuda-driver-stubs")
            self.cuda.requires("cudart")
            self.cuda.requires("nvml-stubs")
        if self.options.xpmem:
            self.requires("xpmem/[^2.6.5]")

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on {self.settings.os}.")
        if self.options.mlx5 and not self.options.verbs:
            raise ConanInvalidConfiguration("Option 'mlx5' requires 'verbs' to be enabled.")
        if self.options.gdrcopy and not self.options.cuda:
            raise ConanInvalidConfiguration("Option 'gdrcopy' requires 'cuda' to be enabled.")

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[<4]")
        self.tool_requires("libtool/[^2.4.7]")
        if self.options.cuda:
            self.cuda.tool_requires("nvcc")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Disable -Werror
        replace_in_file(self, "config/m4/compiler.m4", ' -Werror"', '"')

    def generate(self):
        if not cross_building(self):
            VirtualRunEnv(self).generate(scope="build")

        def enable_disable(opt, val):
            return f"--enable-{opt}" if val else f"--disable-{opt}"

        def with_without(opt, val, pkg=None):
            if val and pkg:
                return f"--with-{opt}={self.dependencies[pkg].package_folder}"
            return f"--with-{opt}" if val else f"--without-{opt}"

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            enable_disable("debug", self.settings.build_type in ["Debug", "RelWithDebInfo"]),
            enable_disable("cma", self.options.cma),
            enable_disable("mt", self.options.multithreading),
            enable_disable("openmp", self.options.openmp),
            enable_disable("tuning", self.options.tuning),
            with_without("bfd", self.options.bfd),
            with_without("cuda", self.options.cuda),
            with_without("dc", self.options.dc),
            with_without("devx", self.options.devx),
            with_without("dm", self.options.dm),
            with_without("fuse3", self.options.fuse3),
            with_without("gdrcopy", self.options.gdrcopy),
            with_without("ib-hw-tm", self.options.ib_hw_tm),
            with_without("mad", self.options.mad, "rdma-core"),
            with_without("mlx5", self.options.mlx5),
            with_without("rc", self.options.rc),
            with_without("rdmacm", self.options.rdmacm, "rdma-core"),
            with_without("ud", self.options.ud),
            with_without("verbs", self.options.verbs),
            with_without("ze", self.options.ze),
            with_without("knem", False),  # No Conan package
            with_without("rocm", False),  # TODO
            with_without("ugni", False),  # No Conan package
            with_without("xpmem", self.options.xpmem, "xpmem"),
            with_without("go", False),
            with_without("java", False),
        ])
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        if self.options.cuda:
            cuda_tc = self.cuda.CudaToolchain()
            cuda_tc.generate()

    def _patch_sources(self):
        if self.options.cuda and not self.dependencies["cudart"].options.shared:
            replace_in_file(self, os.path.join(self.source_folder, "config/m4/cuda.m4"), "cudart", "cudart_static")

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.autoreconf()
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ucx")
        self.cpp_info.set_property("pkg_config_name", "_ucx_aggregate")

        self.cpp_info.components["ucp"].set_property("cmake_target_name", "ucx::ucp")
        self.cpp_info.components["ucp"].set_property("pkg_config_name", "ucx")
        self.cpp_info.components["ucp"].resdirs = ["etc"]
        self.cpp_info.components["ucp"].libs = ["ucp"]
        self.cpp_info.components["ucp"].exelinkflags = ["-Wl,--undefined=ucp_global_init"]
        self.cpp_info.components["ucp"].sharedlinkflags = ["-Wl,--undefined=ucp_global_init"]
        self.cpp_info.components["ucp"].requires = ["uct", "ucs"]

        self.cpp_info.components["uct"].set_property("cmake_target_name", "ucx::uct")
        self.cpp_info.components["uct"].set_property("pkg_config_name", "ucx-uct")
        self.cpp_info.components["uct"].libs = ["uct"]
        self.cpp_info.components["uct"].exelinkflags = ["-Wl,--undefined=uct_init"]
        self.cpp_info.components["uct"].sharedlinkflags = ["-Wl,--undefined=uct_init"]
        self.cpp_info.components["uct"].requires = ["ucs"]

        self.cpp_info.components["ucs"].set_property("cmake_target_name", "ucx::ucs")
        self.cpp_info.components["ucs"].set_property("pkg_config_name", "ucx-ucs")
        self.cpp_info.components["ucs"].libs = ["ucs"]
        self.cpp_info.components["ucs"].exelinkflags = ["-Wl,--undefined=ucs_init"]
        self.cpp_info.components["ucs"].sharedlinkflags = ["-Wl,--undefined=ucs_init"]
        self.cpp_info.components["ucs"].requires = ["ucm"]

        # not exported in CMake or pkg-config
        self.cpp_info.components["ucm"].libs = ["ucm"]
        self.cpp_info.components["ucm"].exelinkflags = ["-Wl,--undefined=ucm_init"]
        self.cpp_info.components["ucm"].sharedlinkflags = ["-Wl,--undefined=ucm_init"]
        if self.options.openmp:
            self.cpp_info.components["ucm"].requires.append("openmp::openmp")

        def _define_component(name, lib, requires, init_symbol=None):
            component = self.cpp_info.components[name]
            component.set_property("pkg_config_name", f"ucx-{name}")
            component.libdirs = ["lib/ucx"]
            component.libs = [lib]
            if init_symbol:
                component.exelinkflags = [f"-Wl,--undefined={init_symbol}"]
                component.sharedlinkflags = [f"-Wl,--undefined={init_symbol}"]
            component.requires = requires
            return component

        if self.options.cuda:
            ucm_cuda = _define_component("cuda", "ucm_cuda", ["ucm", "cudart::cudart_"])
            if self.options.openmp:
                ucm_cuda.requires.append("openmp::openmp")
            _define_component("uct-cuda", "uct_cuda", ["uct", "cuda-driver-stubs::cuda-driver-stubs", "nvml-stubs::nvml-stubs"])
            if self.options.gdrcopy:
                 _define_component("uct-cuda-gdrcopy", "uct_cuda_gdrcopy", ["uct-cuda", "gdrcopy::gdrcopy"])
        if self.options.fuse3:
            _define_component("fuse", "ucs_fuse", ["ucs", "libfuse::libfuse"], "ucs_vfs_fuse_init")
        if self.options.mlx5:
            _define_component("ib-mlx5", "uct_ib_mlx5", ["ib", "rdma-core::libmlx5"], "uct_mlx5_init")
        if self.options.rdmacm:
            _define_component("rdmacm", "uct_rdmacm", ["uct", "rdma-core::librdmacm"], "uct_rdmacm_init")
        if self.options.verbs:
            _define_component("ib", "uct_ib", ["uct", "rdma-core::libibverbs"], "uct_ib_init")
        if self.options.xpmem:
            _define_component("ucx-xpmem", "uct_xpmem", ["uct", "xpmem::xpmem"], "uct_xpmem_init")
        if self.options.ze:
            _define_component("ze", "ucm_ze", ["ucm", "level-zero::level-zero"], "ucm_ze_init")

        if self.options.mad:
            # used only in the perftest executable
            self.cpp_info.components["_perftest"].requires = ["rdma-core::libibmad"]
