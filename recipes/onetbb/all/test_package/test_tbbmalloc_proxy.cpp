#include <oneapi/tbb/tbbmalloc_proxy.h>

#include <cstdlib>

int main() {
    void* memory = std::malloc(64);
    if (!memory) {
        return 1;
    }
    std::free(memory);
    return 0;
}
