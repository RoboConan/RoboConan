#include <spirv_cross_c.h>

int main() {
  spvc_result (*volatile create)(spvc_context*) = spvc_context_create;
  (void)create;
}
