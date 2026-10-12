#include <blasfeo.h>

#if defined(TEST_EXTERNAL_BLAS) && !defined(LA_EXTERNAL_BLAS_WRAPPER)
#error "The external BLAS wrapper configuration is not exported"
#endif

#if defined(TEST_FORTRAN_BLAS_API) && !defined(FORTRAN_BLAS_API)
#error "The Fortran BLAS API configuration is not exported"
#endif

#ifndef TEST_EXTERNAL_BLAS
static bool test_blas_api() {
    char trans = 'N';
    int size = 1;
    double alpha = 1.0;
    double beta = 0.0;
    double a = 2.0;
    double b = 3.0;
    double c = 0.0;
#ifdef TEST_FORTRAN_BLAS_API
    dgemm_(&trans, &trans, &size, &size, &size, &alpha,
           &a, &size, &b, &size, &beta, &c, &size);
#else
    blasfeo_blas_dgemm(&trans, &trans, &size, &size, &size, &alpha,
                       &a, &size, &b, &size, &beta, &c, &size);
#endif
    return c == 6.0;
}
#endif

int main() {
    struct blasfeo_dmat a;
    struct blasfeo_dmat b;
    struct blasfeo_dmat c;
    blasfeo_allocate_dmat(1, 1, &a);
    blasfeo_allocate_dmat(1, 1, &b);
    blasfeo_allocate_dmat(1, 1, &c);

    double a_value = 2.0;
    double b_value = 3.0;
    blasfeo_pack_dmat(1, 1, &a_value, 1, &a, 0, 0);
    blasfeo_pack_dmat(1, 1, &b_value, 1, &b, 0, 0);
    blasfeo_dgemm_nn(1, 1, 1, 1.0, &a, 0, 0, &b, 0, 0,
                     0.0, &c, 0, 0, &c, 0, 0);

    double result = 0.0;
    blasfeo_unpack_dmat(1, 1, &c, 0, 0, &result, 1);
    blasfeo_free_dmat(&a);
    blasfeo_free_dmat(&b);
    blasfeo_free_dmat(&c);
    if (result != 6.0) {
        return 1;
    }
#ifndef TEST_EXTERNAL_BLAS
    return test_blas_api() ? 0 : 1;
#endif
}
