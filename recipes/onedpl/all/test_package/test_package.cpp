#include <vector>
#include <oneapi/dpl/execution>
#include <oneapi/dpl/algorithm>

#ifdef TEST_ONEDPL_SYCL
void compile_sycl_backend()
{
    std::vector<int> data(1);
    std::fill_n(oneapi::dpl::execution::dpcpp_default,
                data.begin(), data.size(), -1);
}
#endif

int main()
{
    std::vector<int> data(10000000);
    auto policy = oneapi::dpl::execution::par_unseq;
    std::fill_n(policy, data.begin(), data.size(), -1);

    return 0;
}
