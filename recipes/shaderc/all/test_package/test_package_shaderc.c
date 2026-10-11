#include <shaderc/shaderc.h>

int main() {
  shaderc_compiler_t (*volatile initialize)(void) = shaderc_compiler_initialize;
  (void)initialize;
}
