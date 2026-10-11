#include <glslang/Public/ShaderLang.h>

int main() {
  auto* volatile initialize = &glslang::InitializeProcess;
  (void)initialize;
}
