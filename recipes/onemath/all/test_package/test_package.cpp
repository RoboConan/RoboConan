#include <oneapi/math.hpp>
#include <sycl/sycl.hpp>

void dummy() {
    sycl::queue q;
    int n = 10;
    float* vec = sycl::malloc_device<float>(n * sizeof(float), q);
    float* out = sycl::malloc_device<float>(n * sizeof(float), q);
    q.memset(vec, 0, n * sizeof(float)).wait();
    oneapi::math::blas::column_major::asum(
        oneapi::math::backend_selector<oneapi::math::backend::mklcpu>{ q }, n, vec, 1, out).wait();
    sycl::free(vec, q);
    sycl::free(out, q);
}

int main() {}
