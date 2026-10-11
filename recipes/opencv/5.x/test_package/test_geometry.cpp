#include <opencv2/geometry.hpp>

int main() {
    auto rotation = cv::getRotationMatrix2D(cv::Point2f(), 0.0, 1.0);
    return 0;
}
