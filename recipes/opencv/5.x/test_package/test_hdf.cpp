#include <opencv2/hdf/hdf5.hpp>

int main() {
    cv::Ptr<cv::hdf::HDF5> (*volatile open_hdf)(const cv::String&) = &cv::hdf::open;
    return open_hdf == nullptr;
}
