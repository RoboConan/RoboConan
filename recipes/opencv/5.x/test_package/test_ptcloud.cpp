#include <opencv2/ptcloud.hpp>

int main() {
    auto input = cv::Mat::ones(1, 1, CV_16UC1);
    cv::Mat output;
    cv::rescaleDepth(input, CV_32FC1, output);

    return 0;
}
