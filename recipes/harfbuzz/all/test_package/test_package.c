#include <stdio.h>
#include <string.h>
#include <hb.h>
#ifdef WITH_HARFBUZZ_RASTER
#include <hb-raster.h>
#endif
#ifdef WITH_HARFBUZZ_VECTOR
#include <hb-vector.h>
#endif
#ifdef WITH_HARFBUZZ_GPU
#include <hb-gpu.h>
#endif

int main() {
    const char *version = hb_version_string();
    printf("harfbuzz version: %s\n", version);
    return 0;
}
