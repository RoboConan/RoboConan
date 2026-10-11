#include <opencv2/imgcodecs.hpp>

int main() {
    bool (*volatile imwrite_image)(const cv::String&, cv::InputArray, const std::vector<int>&) = &cv::imwrite;
    return imwrite_image == nullptr;
}
