#include <XDSP.h>

int main() {
    constexpr size_t length = 64;
    alignas(16) DirectX::XMVECTOR real[length / 4]{};
    alignas(16) DirectX::XMVECTOR imaginary[length / 4]{};
    alignas(16) DirectX::XMVECTOR unity[length]{};
    XDSP::FFTInitializeUnityTable(unity, length);
    XDSP::FFTInterleaved(real, imaginary, unity, 1, 6);
    XDSP::IFFTDeinterleaved(real, imaginary, unity, 1, 6);
}
