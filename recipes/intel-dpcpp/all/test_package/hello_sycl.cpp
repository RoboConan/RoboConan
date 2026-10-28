#include <sycl/sycl.hpp>

int main() {
    auto platforms = sycl::platform::get_platforms();
    return platforms.size() > 255;
}
