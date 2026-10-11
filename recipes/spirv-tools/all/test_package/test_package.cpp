#include "spirv/unified1/spirv.hpp"
#include "spirv-tools/libspirv.hpp"
#include "spirv-tools/optimizer.hpp"

int main() {
  const uint32_t word = static_cast<uint32_t>(spv::OpNop);
  spvtools::SpirvTools core(SPV_ENV_UNIVERSAL_1_3);
  core.Validate(&word, 1);
  spvtools::Optimizer opt(SPV_ENV_UNIVERSAL_1_3);
}
