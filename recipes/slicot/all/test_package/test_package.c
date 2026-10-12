#include <complex.h>
#include <stdint.h>

#ifdef TEST_SLICOT_INTEGER8
typedef int64_t slicot_int;
#else
typedef int slicot_int;
#endif

void ma02bz_(const char *side, const slicot_int *m, const slicot_int *n,
             double _Complex *a, const slicot_int *lda);

int main(void) {
    const char side = 'B';
    const slicot_int m = 2, n = 3, lda = 2; // lda >= m
    // A in column-major: columns are contiguous blocks of lda
    double _Complex A[2 * 3] = {
        1.0 + 0.0*I, 2.0 + 0.0*I,   // column 1
        3.0 + 0.0*I, 4.0 + 0.0*I,   // column 2
        5.0 + 0.0*I, 6.0 + 0.0*I    // column 3
    };
    ma02bz_(&side, &m, &n, A, &lda);
}
