#include <glim/common/imu_integration.hpp>
#include <glim/common/imu_validation.hpp>
#include <glim/mapping/global_mapping_base.hpp>
#include <glim/util/config.hpp>

#include <iostream>

int main(int argc, char** argv) {
    glim::GlobalConfig::instance(argc > 1 ? argv[1] : "");
    glim::IMUIntegration imu_integration;
    std::cout << "Number of IMU values in queue: " << imu_integration.imu_data_in_queue().size() << std::endl;
}
