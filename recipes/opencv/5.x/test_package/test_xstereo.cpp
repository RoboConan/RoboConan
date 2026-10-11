#include <opencv2/xstereo.hpp>

int main() {
    auto matcher = cv::stereo::StereoBinaryBM::create(16, 9);
    return 0;
}
