#include <opencv2/core.hpp>
#include <opencv2/objdetect.hpp>
#include <opencv2/objdetect/aruco_dictionary.hpp>
#include <opencv2/objdetect/mcc_checker_detector.hpp>

int main() {
    auto dictionary = cv::aruco::getPredefinedDictionary(cv::aruco::DICT_6X6_250);
    auto checker_detector = cv::mcc::CCheckerDetector::create();

    return 0;
}
