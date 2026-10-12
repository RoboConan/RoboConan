from typing import Union

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.scm import Version

cuda_supported_arch_ranges = {
    9: (30, 70),
    10: (30, 75),
    11: (35, 90),
    12: (50, 121),
    13: (75, None),
}

packages_following_ctk_minor_version = {
    "cublas",
    "cuda-crt",
    "cuda-driver-stubs",
    "cuda-gdb",
    "cuda-opencl",
    "cuda-profiler-api",
    "cuda-sanitizer-api",
    "cuda-tileiras",
    "cudart",
    "cudla",
    "culibos",
    "cupti",
    "nvcc",
    "nvfatbin",
    "nvml-stubs",
    "nvptxcompiler",
    "nvrtc",
    "nvvm",
}
packages_following_ctk_major_version = {
    "cuda-samples",
    "npp",
    "nvjitlink",
    "nvjpeg",
    "nvidia-video-codec-sdk",
}

def check_min_cuda_architecture(conanfile: ConanFile, min_arch: Union[str, int]):
    """Raises a ConanInvalidConfiguration if any of the architectures in 'cuda.architectures' setting
    are below the given minimum architecture.

    :param conanfile: The current recipe object. Always use ``self``.
    :param min_arch: Minimal CUDA architecture to check against, e.g. "70" or "80".
    """
    if not conanfile.settings.get_safe("cuda.architectures"):
        raise ConanInvalidConfiguration("No 'cuda.architectures' setting defined.")
    min_arch = int(min_arch)
    architectures = str(conanfile.settings.cuda.architectures).strip()
    for arch in architectures.split(","):
        if arch == "native":
            # Can't check
            continue
        if arch in ["all", "all-major"]:
            cuda_major = int(Version(conanfile.settings.cuda.version).major.value)
            supported_range = cuda_supported_arch_ranges[cuda_major]
            if min_arch > supported_range[0]:
                raise ConanInvalidConfiguration(
                    f"Can't use cuda.architectures={architectures}: {conanfile.name} requires at least {min_arch},"
                    f" but 'all' will cover {supported_range[0]} to {supported_range[1] or 'latest'}."
                )
        arch = arch.split("-", 1)[0]
        if int(arch) < min_arch:
            raise ConanInvalidConfiguration(
                f"cuda.architectures={architectures} is below the minimum required of {min_arch} by {conanfile.name}."
            )


def get_version_range(_: ConanFile, package_name, cuda_version):
    """Returns the version range that is compatible with the given CUDA (major) version for a CUDA Toolkit package."""
    cuda_version = Version(str(cuda_version))
    cuda_major = int(cuda_version.major.value)
    if package_name in packages_following_ctk_minor_version:
        if cuda_version.minor is None:
            return f"^{cuda_major}"
        return f"~{cuda_version.major}.{cuda_version.minor}"
    if package_name in packages_following_ctk_major_version:
        return f"^{cuda_major}"
    if package_name == "cucollections":
        if cuda_major >= 13:
            return ">0.0.1+git.20250529"
        else:
            return "<=0.0.1+git.20250529"
    if package_name == "cuda-cccl":
        if cuda_major >= 13:
            return "^3"
        elif cuda_version >= "12.2":
            return "^2"
        else:
            return "^1"
    if package_name == "cudss":
        if cuda_major >= 13:
            return ">=0.7"
        elif cuda_major == 12:
            return ">=0.3 <0.7"
        else:
            return "<0.3"
    if package_name == "cufft":
        return f"^{cuda_major - 1}"
    if package_name == "cufile":
        if cuda_major >= 13:
            return ">=1.15"
        elif cuda_major == 12:
            return ">=1.5 <1.15"
        else:
            return "<1.5"
    if package_name == "cuquantum":
        if cuda_major >= 13:
            return ">=25.09"
        elif cuda_major == 12:
            return "*"
        else:
            return "<25.09"
    if package_name == "curand":
        if cuda_major >= 13:
            return "~10.4"
        elif cuda_major == 12:
            return "~10.3"
        else:
            return "~10.2"
    if package_name == "cusolver":
        return "^12" if cuda_major >= 13 else "^11"
    if package_name == "cusolvermp":
        if cuda_major >= 13:
            return ">=0.7"
        elif cuda_major == 12:
            return "*"
        else:
            return "<0.6"
    if package_name == "cusparse":
        if cuda_major >= 13:
            return ">=12.6"
        elif cuda_major == 12:
            return ">=12 <12.6"
        else:
            return "^11"
    if package_name == "cusparselt":
        if cuda_major >= 13:
            return ">=0.8"
        elif cuda_major == 12:
            return "*"
        else:
            return "<0.8"
    if package_name == "cutensor":
        if cuda_major >= 13:
            return "^2.3"
        elif cuda_major == 12:
            return ">=1 <3"
        else:
            return "<2.3"
    if package_name == "cutensornet":
        if cuda_major >= 13:
            return "^2.9"
        elif cuda_major == 12:
            return ">=2 <3"
        else:
            return "<2.9.0"
    if package_name == "nvcomp":
        if cuda_major >= 13:
            return ">=5"
        else:
            return "<6"
    if package_name == "nvjpeg2k":
        if cuda_major >= 13:
            return ">=0.9"
        else:
            return "<0.9"
    if package_name == "nvtiff":
        if cuda_major >= 13:
            return ">=0.5 <1"
        else:
            return "<0.6"
    if package_name == "nvimgcodec":
        return "*"
    if package_name == "nvidia-optical-flow-sdk":
        return "^5"
    if package_name == "nvtx":
        return "^3"
    raise ConanException(f"Unknown CUDA package name: {package_name}")


def requires(conanfile: ConanFile, package_name: str, **kwargs):
    """A convenience function to require a CUDA package with the correct version range.
    It will automatically determine the version range based on the cuda.version setting.

    :param conanfile: The current recipe object. Always use ``self``.
    :param package_name: Name of the CUDA package, e.g. "cudart", "cublas", etc.
    :param kwargs: Additional keyword arguments to pass to `conanfile.requires()`.
    """
    version_range = get_version_range(conanfile, package_name, conanfile.settings.cuda.version)
    conanfile.requires(f"{package_name}/[{version_range}]", **kwargs)


def tool_requires(conanfile: ConanFile, package_name: str, **kwargs):
    version_range = get_version_range(conanfile, package_name, conanfile.settings.cuda.version)
    conanfile.tool_requires(f"{package_name}/[{version_range}]", **kwargs)


__all__ = [
    "check_min_cuda_architecture",
    "cuda_supported_arch_ranges",
    "get_version_range",
    "requires",
    "tool_requires",
    "packages_following_ctk_minor_version"
]
