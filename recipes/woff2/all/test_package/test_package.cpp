#include <woff2/decode.h>
#include <cstdio>

int main() {
    // Minimal test: call the API with empty input (should fail gracefully)
    size_t out_size = woff2::ComputeWOFF2FinalSize(nullptr, 0);
    printf("woff2::ComputeWOFF2FinalSize(nullptr, 0) = %zu\n", out_size);
    return 0;
}
