#include <kai/ukernels/matmul/matmul_clamp_f32_f32_f32p/kai_matmul_clamp_f32_f32_f32p8x1biasf32_6x8x4_neon_mla.h>
#ifdef WITH_EXPERIMENTAL_OPS
#include <kai/ops/conv/depthwise_common.hpp>
#endif

int main() {
    kai_get_m_step_matmul_clamp_f32_f32_f32p8x1biasf32_6x8x4_neon_mla();
#ifdef WITH_EXPERIMENTAL_OPS
    kai::ops::depthwise::get_reduced_view_for_dilation(1, 1, 0, 1, 1, 1, 0);
#endif
}
