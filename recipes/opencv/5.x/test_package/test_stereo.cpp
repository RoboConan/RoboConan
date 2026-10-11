#include <opencv2/stereo.hpp>

int main() {
    auto matcher = cv::StereoBM::create(16, 9);
    return 0;
}
