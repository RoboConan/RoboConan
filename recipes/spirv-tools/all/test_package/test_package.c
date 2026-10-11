#include "spirv-tools/libspirv.h"

int main()
{
  spv_context (*volatile create)(spv_target_env) = spvContextCreate;
  (void)create;
}
