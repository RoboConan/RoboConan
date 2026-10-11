#ifdef USE_OPENCL_HPP
#include <CL/opencl.hpp>
#else
#include <CL/cl2.hpp>
#endif

int main() {
    cl::Context *context = nullptr;
    (void)context;
}
