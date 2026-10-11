#include <cblas.h>
#ifdef OPENBLAS_TEST_FORTRAN
#include <f77blas.h>
#endif
#if defined(OPENBLAS_TEST_LAPACKE) && !defined(OPENBLAS_TEST_FORTRAN)
#include <lapacke.h>
#endif
#include <stdio.h>

void test_cblas() {
  double A[6] = {1.0,2.0,1.0,-3.0,4.0,-1.0};
  double B[6] = {1.0,2.0,1.0,-3.0,4.0,-1.0};
  double C[9] = {.5,.5,.5,.5,.5,.5,.5,.5,.5};
  cblas_dgemm(CblasColMajor, CblasNoTrans, CblasTrans,3,3,2,1,A, 3, B, 3,2,C,3);

  for(int i=0; i<9; i++)
    printf("%lf ", C[i]);
  printf("\n");
}

#ifdef OPENBLAS_TEST_FORTRAN
void test_f77blas() {
  double A[6] = {1.0,2.0,1.0,-3.0,4.0,-1.0};
  double B[6] = {1.0,2.0,1.0,-3.0,4.0,-1.0};
  double C[9] = {.5,.5,.5,.5,.5,.5,.5,.5,.5};
  char transa = 'N';
  char transb = 'T';
  blasint m = 3;
  blasint n = 3;
  blasint k = 2;
  blasint lda = 3;
  blasint ldb = 3;
  blasint ldc = 3;
  double alpha = 1.0;
  double beta  = 2.0;
  dgemm_(&transa, &transb, &m, &n, &k, &alpha, A, &lda, B, &ldb, &beta, C, &ldc);

  for(int i=0; i<9; i++)
    printf("%lf ", C[i]);
  printf("\n");
}
#endif

#if defined(OPENBLAS_TEST_LAPACKE) && !defined(OPENBLAS_TEST_FORTRAN)
void test_lapacke() {
  double A[4] = {1.0, 2.0, 3.0, 4.0};
  double B[2] = {5.0, 6.0};
  lapack_int ipiv[2];
  LAPACKE_dgesv(LAPACK_COL_MAJOR, 2, 1, A, 2, ipiv, B, 2);
}
#endif

int main()
{
  test_cblas();
#ifdef OPENBLAS_TEST_FORTRAN
  test_f77blas();
#endif
#if defined(OPENBLAS_TEST_LAPACKE) && !defined(OPENBLAS_TEST_FORTRAN)
  test_lapacke();
#endif
}
