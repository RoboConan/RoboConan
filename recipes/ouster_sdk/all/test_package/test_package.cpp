#include <ouster/lidar_scan.h>

#ifdef WITH_OSF
#include <ouster/osf/writer.h>
#endif
#ifdef WITH_PCAP
#include <ouster/os_pcap.h>
#endif
#ifdef WITH_VIZ
#include <ouster/point_viz.h>
#endif
#ifdef WITH_SENSOR
#include <ouster/sensor_scan_source.h>
#include <ouster/scan_source.h>
#endif
#ifdef WITH_MAPPING
#include <ouster/slam_engine.h>
#endif

#include <iostream>
#include <vector>
#include <string>

int main() {
    size_t w = 100;
    size_t h = 100;
    using namespace ouster::sdk;
    core::LidarScan scan(w, h, core::UDPProfileLidar::RNG19_RFL8_SIG16_NIR16_DUAL);
    std::cout << "Successfully created a sensor::LidarScan object" << std::endl;

#ifdef WITH_OSF
    osf::Writer writer("tmp.osf");
    std::cout << "Successfully created a osf::Writer object" << std::endl;
#endif

#ifdef WITH_PCAP
    try {
        pcap::PcapReader pcap_reader("tmp.pcap");
    } catch (...) { }
    std::cout << "Successfully created a sensor_utils::PcapReader object" << std::endl;
#endif

#ifdef WITH_VIZ
    viz::PointViz viz("Viz example");
    std::cout << "Successfully created a viz::PointViz object" << std::endl;
#endif

#ifdef WITH_SENSOR
    std::vector<std::string> sources;
    ScanSourceOptions options;
    sensor::SensorScanSource sensor_source(sources, options);
    std::cout << "Successfully created a SensorScanSource object" << std::endl;
#endif

#ifdef WITH_MAPPING
    mapping::SlamConfig slam_config;
    try {
        mapping::SlamEngine slam_engine({}, slam_config);
    } catch (...) { }
    std::cout << "Successfully verified mapping component" << std::endl;
#endif
}
