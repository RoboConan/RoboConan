#include <opencv2/features.hpp>

int main() {
    auto matcher = cv::DescriptorMatcher::create(cv::DescriptorMatcher::BRUTEFORCE);
    return 0;
}
