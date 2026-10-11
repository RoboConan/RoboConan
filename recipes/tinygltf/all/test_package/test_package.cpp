#ifdef TINYGLTF_HEADER_ONLY
#define TINYGLTF_IMPLEMENTATION
#define STB_IMAGE_IMPLEMENTATION
#define STB_IMAGE_WRITE_IMPLEMENTATION
#endif
#include <tiny_gltf.h>

int main() {
  tinygltf::GetComponentSizeInBytes(TINYGLTF_COMPONENT_TYPE_FLOAT);
}
