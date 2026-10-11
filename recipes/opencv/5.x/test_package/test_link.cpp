#if defined(TEST_OPENCV_MODULE_CUDAARITHM)
#include <opencv2/cudaarithm.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDABGSEGM)
#include <opencv2/cudabgsegm.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDACODEC)
#include <opencv2/cudacodec.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDAFEATURES2D)
#include <opencv2/cudafeatures2d.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDAFILTERS)
#include <opencv2/cudafilters.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDAIMGPROC)
#include <opencv2/cudaimgproc.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDALEGACY)
#include <opencv2/cudalegacy.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDAOBJDETECT)
#include <opencv2/cudaobjdetect.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDAOPTFLOW)
#include <opencv2/cudaoptflow.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDASTEREO)
#include <opencv2/cudastereo.hpp>
#elif defined(TEST_OPENCV_MODULE_CUDAWARPING)
#include <opencv2/cudawarping.hpp>
#elif defined(TEST_OPENCV_MODULE_CVV)
#include <opencv2/cvv/final_show.hpp>
#elif defined(TEST_OPENCV_MODULE_DNN_OBJDETECT)
#include <opencv2/core_detect.hpp>
#elif defined(TEST_OPENCV_MODULE_DPM)
#include <opencv2/dpm.hpp>
#elif defined(TEST_OPENCV_MODULE_OVIS)
#include <opencv2/ovis.hpp>
#elif defined(TEST_OPENCV_MODULE_RAPID)
#include <opencv2/rapid.hpp>
#elif defined(TEST_OPENCV_MODULE_VIDEOSTAB)
#include <opencv2/videostab.hpp>
#elif defined(TEST_OPENCV_MODULE_VIZ)
#include <opencv2/viz.hpp>
#endif

int main() {
    volatile bool use_symbol = false;
    if (use_symbol) {
#if defined(TEST_OPENCV_MODULE_CUDAARITHM)
        cv::cuda::add(cv::noArray(), cv::noArray(), cv::noArray());
#elif defined(TEST_OPENCV_MODULE_CUDABGSEGM)
        cv::cuda::createBackgroundSubtractorMOG();
#elif defined(TEST_OPENCV_MODULE_CUDACODEC)
        cv::cudacodec::createVideoReader(cv::String());
#elif defined(TEST_OPENCV_MODULE_CUDAFEATURES2D)
        cv::cuda::createHarrisCorner(CV_8UC1, 3, 3, 0.04);
#elif defined(TEST_OPENCV_MODULE_CUDAFILTERS)
        cv::cuda::createBoxFilter(CV_8UC1, CV_8UC1, cv::Size(3, 3));
#elif defined(TEST_OPENCV_MODULE_CUDAIMGPROC)
        cv::cuda::cvtColor(cv::noArray(), cv::noArray(), cv::COLOR_BGR2GRAY);
#elif defined(TEST_OPENCV_MODULE_CUDALEGACY)
        cv::cuda::createImagePyramid(cv::noArray());
#elif defined(TEST_OPENCV_MODULE_CUDAOBJDETECT)
        cv::cuda::HOG::create();
#elif defined(TEST_OPENCV_MODULE_CUDAOPTFLOW)
        cv::cuda::SparsePyrLKOpticalFlow::create();
#elif defined(TEST_OPENCV_MODULE_CUDASTEREO)
        cv::cuda::createStereoBM();
#elif defined(TEST_OPENCV_MODULE_CUDAWARPING)
        cv::cuda::resize(cv::noArray(), cv::noArray(), cv::Size());
#elif defined(TEST_OPENCV_MODULE_CVV)
        cvv::impl::finalShow();
#elif defined(TEST_OPENCV_MODULE_DNN_OBJDETECT)
        cv::dnn_objdetect::InferBbox(cv::Mat(), cv::Mat(), cv::Mat());
#elif defined(TEST_OPENCV_MODULE_DPM)
        cv::dpm::DPMDetector::create({});
#elif defined(TEST_OPENCV_MODULE_OVIS)
        cv::ovis::addResourceLocation("");
#elif defined(TEST_OPENCV_MODULE_RAPID)
        cv::rapid::drawSearchLines(cv::noArray(), cv::noArray(), cv::Scalar());
#elif defined(TEST_OPENCV_MODULE_VIDEOSTAB)
        cv::videostab::calcBlurriness(cv::Mat());
#elif defined(TEST_OPENCV_MODULE_VIZ)
        cv::viz::makeCameraPose(cv::Vec3d(), cv::Vec3d(), cv::Vec3d());
#endif
    }
    return 0;
}
