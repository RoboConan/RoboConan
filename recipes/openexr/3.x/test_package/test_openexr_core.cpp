#include <OpenEXR/openexr_encode.h>

int main()
{
    auto volatile initialize = &exr_encoding_initialize;
    return initialize == nullptr;
}
