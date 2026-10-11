#include <opencv2/signal.hpp>

int main() {
    auto input = cv::Mat::ones(1, 4, CV_32FC1);
    cv::Mat output;
    cv::signal::resampleSignal(input, output, 1000, 1000);

    return 0;
}
