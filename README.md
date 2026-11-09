RoboConan
=========

RoboConan is a recipes-only Conan repository, forked from ConanCenter to
deliver faster iteration, broader coverage (CV/ML/robotics, especially on
edge devices), and greater control over your dependency graph.

No pre-built binaries will be provided by design:

- Minimal defaults – we avoid enabling most options "just in case."
  Packages and dependency trees are much leaner by default with optional components enabled only as-needed by consuming recipes.
- Liberal use of version ranges – version bumps to central packages don't trigger a rebuild of the whole universe.
- Less administrative overhead – the focus is on improving the choice and quality of the packages themselves, not on maintaining the infrastructure.

We encourage users and organizations to host their own binary repositories, with the exact feature sets and build profiles they need, instead of relying on a centrally-managed one.
We plan to offer additional tooling and examples to streamline that process in the future.

While this repository is not compatible with ConanCenter, we continuously sync changes from upstream.
As a result, the packages here are always at least as new, and generally much more up to date, than those on ConanCenter.

## Highlights

The most notable additions in this repository are:
- Full [CUDA](https://developer.nvidia.com/cuda-toolkit) support at both the language and Toolkit level. All of Nvidia's binary packages are available as well as nearly all of their open-source projects.
  Optional CUDA support has been added to all recipes that have the capability.
- [TensorRT](https://developer.nvidia.com/tensorrt), plus CUDA-capable [ONNX Runtime](https://onnxruntime.ai/) and [PyTorch](https://pytorch.org/) recipes.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) and [whisper.cpp](https://github.com/ggml-org/whisper.cpp) with CUDA and all other backends supported.
- Full [Intel oneAPI](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html) support ([oneMKL](https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html), [oneDNN](https://github.com/uxlfoundation/oneDNN), [oneMath](https://github.com/uxlfoundation/oneMath), etc). Intel oneAPI [DPC++/C++ Compiler](https://www.intel.com/content/www/us/en/developer/tools/oneapi/dpc-compiler.html) toolchain is provided for SYCL support.
- Recipes for [SuiteSparse](https://people.engr.tamu.edu/davis/suitesparse.html), [Ceres](http://ceres-solver.org/), [GTSAM](https://gtsam.org/), [g2o](https://github.com/RainerKuemmerle/g2o), [SymForce](https://symforce.org/), [COLMAP](https://colmap.github.io/), [GLOMAP](https://github.com/colmap/glomap), [OpenMVG](https://github.com/openMVG/openMVG), [Faiss](https://faiss.ai/), [Open3D](https://www.open3d.org/), [PCL](https://pointclouds.org/), [BASALT](https://github.com/VladyslavUsenko/basalt), [stella_vslam](https://stella-cv.readthedocs.io/), [GLIM](https://github.com/Koide3/glim), [Rerun](https://www.rerun.io/), and [Foxglove](https://foxglove.dev/).
- Both [Eigen](https://eigen.tuxfamily.org/) 5.0.0 and 3.4.1 are supported in all recipes that rely on it.
- A comprehensive collection of solvers:
    - most [COIN-OR](https://www.coin-or.org/) libraries with all optional features,
    - [SCIP Optimization Suite](https://www.scipopt.org/),
    - Google's [OR-Tools](https://developers.google.com/optimization),
    - [cuOPT](https://github.com/NVIDIA/cuopt),
    - all major commercial solvers ([Gurobi](https://www.gurobi.com/), [CPLEX](https://www.ibm.com/products/ilog-cplex-optimization-studio), [Xpress](https://www.fico.com/en/products/fico-xpress-optimization), [MOSEK](https://www.mosek.com/), [Knitro](https://www.artelys.com/solvers/knitro/), etc),
    - fully-featured [CasADi](https://web.casadi.org/) and [acados](https://docs.acados.org/).
- BLAS and LAPACK meta-packages with easily-swappable choice of implementation:
    - [OpenBLAS](https://github.com/OpenMathLib/OpenBLAS), [oneMKL](https://www.intel.com/content/www/us/en/developer/tools/oneapi/onemkl.html) and [BLIS](https://github.com/flame/blis) for x86_64;
    - [BLIS](https://github.com/flame/blis), [OpenBLAS](https://github.com/OpenMathLib/OpenBLAS), [ArmPL](https://developer.arm.com/Tools%20and%20Software/Arm%20Performance%20Libraries) (Arm Performance Libraries), [NVPL](https://docs.nvidia.com/nvpl/latest/index.html) for armv8.
- The full suite of [GStreamer](https://gstreamer.freedesktop.org/) and its 250+ plugins is supported.
- Versions of [LLVM](https://llvm.org/) and [Clang](https://clang.llvm.org/) that actually work and are used by a few compiler toolchains (e.g. for shaders and other domain-specific IR compilation).
- Complete recipes for [Python](https://www.python.org/), [Rust](https://www.rust-lang.org/), [Go](https://go.dev/), [Julia](https://julialang.org/) and [Octave](https://octave.org/) to allow building of bindings in either direction.
    - A [PythonVenv](https://github.com/conan-kiln/kiln/blob/main/recipes/conan-utils/all/src/python_venv.py) generator is also provided to streamline the installation of Python build-time dependencies.
- Better-maintained [Vulkan SDK](https://vulkan.lunarg.com/) and other graphics suites. Recipes for [Filament](https://github.com/google/filament), [Skia](https://skia.org/), [Dawn](https://github.com/google/dawn) and [Embree](https://www.embree.org/) are available.
- Fortran is supported for reference [LAPACK](https://github.com/Reference-LAPACK/lapack) and other numerical libraries.
- All libraries have been tested and fixed as necessary to support for cross-compilation to linux-aarch64.
- [libjpeg](https://libjpeg.sourceforge.net/) and [zlib](https://zlib.net/) have been swapped out for [libjpeg-turbo](https://libjpeg-turbo.org/) and [zlib-ng](https://github.com/zlib-ng/zlib-ng) everywhere for improved performance, matching the behavior of most mainstream distros.
- and much, much more...

In total, 440 additional recipes and 8,000 commits on top of ConanCenter as of 2025-09.
## Setup

You can add this repo as a Conan remote with the following commands:

```
git clone https://github.com/RoboConan/RoboConan.git
conan remote add roboconan "$PWD/RoboConan"
```

Requires Conan v2.2 or newer.
