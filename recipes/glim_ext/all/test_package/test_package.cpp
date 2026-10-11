#include <glim_ext/util/config_ext.hpp>

#include <string>

int main(int argc, char** argv) {
    const std::string config_file = std::string(argc > 1 ? argv[1] : "") + "/config_ext.json";
    const glim::Config config(config_file);
    return config.has_param("global_ext", "config_path") ? 0 : 1;
}
