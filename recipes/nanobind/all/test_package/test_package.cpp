#include <nanobind/nanobind.h>

namespace nb = nanobind;
using namespace nb::literals;

#ifndef TEST_MODULE
#define TEST_MODULE test_package_static
#endif

NB_MODULE(TEST_MODULE, m) {
    m.def("add", [](int a, int b) { return a + b; }, "a"_a, "b"_a);
}
