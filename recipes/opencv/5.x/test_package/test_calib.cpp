#include <opencv2/calib.hpp>

#include <vector>

int main() {
    std::vector<std::vector<cv::Point3f>> object_points{{
        {0.0f, 0.0f, 0.0f}, {1.0f, 0.0f, 0.0f},
        {0.0f, 1.0f, 0.0f}, {1.0f, 1.0f, 0.0f}
    }};
    std::vector<std::vector<cv::Point2f>> image_points{{
        {100.0f, 100.0f}, {200.0f, 100.0f},
        {100.0f, 200.0f}, {200.0f, 200.0f}
    }};
    auto camera_matrix = cv::initCameraMatrix2D(object_points, image_points, cv::Size(640, 480));

    return 0;
}
