#include <ggml.h>
#include <stdio.h>

#ifdef GGML_TEST_CPU
#include <ggml-cpu.h>
#endif
#ifdef GGML_TEST_BLAS
#include <ggml-blas.h>
#endif
#ifdef GGML_TEST_CUDA
#include <ggml-cuda.h>
#endif
#ifdef GGML_TEST_METAL
#include <ggml-metal.h>
#endif
#ifdef GGML_TEST_OPENCL
#include <ggml-opencl.h>
#endif
#ifdef GGML_TEST_RPC
#include <ggml-rpc.h>
#endif
#ifdef GGML_TEST_SYCL
#include <ggml-sycl.h>
#endif
#ifdef GGML_TEST_VULKAN
#include <ggml-vulkan.h>
#endif

int main() {
    printf("GGML version: %s\n", ggml_version());
#ifdef GGML_TEST_CPU
    (void) ggml_backend_cpu_reg();
#endif
#ifdef GGML_TEST_BLAS
    (void) ggml_backend_blas_reg();
#endif
#ifdef GGML_TEST_CUDA
    (void) ggml_backend_cuda_reg();
#endif
#ifdef GGML_TEST_METAL
    (void) ggml_backend_metal_reg();
#endif
#ifdef GGML_TEST_OPENCL
    (void) ggml_backend_opencl_reg();
#endif
#ifdef GGML_TEST_RPC
    (void) ggml_backend_rpc_reg();
#endif
#ifdef GGML_TEST_SYCL
    (void) ggml_backend_sycl_reg();
#endif
#ifdef GGML_TEST_VULKAN
    (void) ggml_backend_vk_reg();
#endif
}
