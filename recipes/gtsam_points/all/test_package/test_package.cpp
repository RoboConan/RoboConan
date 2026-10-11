#include <gtsam_points/factors/linear_damping_factor.hpp>
#include <gtsam_points/util/indexed_sliding_window.hpp>
#include <gtsam_points/util/runnning_statistics.hpp>

#include <iostream>
#include <memory>

int main() {
    auto factor = std::make_shared<gtsam_points::LinearDampingFactor>('x', 1, 2);
    std::cout << "Factor key: " << (char)factor->keys().front() << std::endl;
}
