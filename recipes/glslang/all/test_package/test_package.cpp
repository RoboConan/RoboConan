#include <glslang/Public/ResourceLimits.h>
#include <glslang/Public/ShaderLang.h>

#include <iostream>

int main() {
  std::cout << glslang::GetGlslVersionString() << '\n';
  return GetDefaultResources() ? 0 : 1;
}
