#include <colmap/controllers/option_manager.h>
#include <colmap/scene/reconstruction.h>
#include <colmap/sfm/global_mapper.h>
#include <colmap/util/logging.h>

int main(int argc, char** argv) {
  colmap::InitializeGlog(argv);
  colmap::OptionManager options;
  options.Parse(argc, argv);
  colmap::GlobalMapperOptions global_mapper_options;
  colmap::Reconstruction reconstruction;
}
