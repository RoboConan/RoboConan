#include <oneapi/tbb/blocked_range.h>
#include <oneapi/tbb/parallel_reduce.h>
#include <oneapi/tbb/version.h>

#include <iostream>

int main() {
    const int sum = oneapi::tbb::parallel_reduce(
        oneapi::tbb::blocked_range<int>(1, 101),
        0,
        [](const oneapi::tbb::blocked_range<int>& range, int value) {
            for (int number = range.begin(); number != range.end(); ++number) {
                value += number;
            }
            return value;
        },
        [](int lhs, int rhs) { return lhs + rhs; });

    std::cout << "tbb runtime version: " << TBB_runtime_version() << "\n";
    std::cout << "tbb runtime interface version: " << TBB_runtime_interface_version() << "\n";
    return sum == 5050 ? 0 : 1;
}
