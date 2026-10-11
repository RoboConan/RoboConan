#include <opencv2/core.hpp>
#include <opencv2/photo.hpp>
#include <opencv2/photo/ccm.hpp>

int main() {
    auto src_image = cv::Mat::zeros(400, 400, CV_8UC3);
    cv::Mat dst_image;
    cv::fastNlMeansDenoising(src_image, dst_image);
    cv::ccm::ColorCorrectionModel color_correction_model;

    return 0;
}
