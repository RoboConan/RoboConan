#include <oneapi/tbb/scalable_allocator.h>

int main() {
    oneapi::tbb::scalable_allocator<int> allocator;
    int* values = allocator.allocate(4);
    values[0] = 42;
    const bool success = values[0] == 42;
    allocator.deallocate(values, 4);
    return success ? 0 : 1;
}
