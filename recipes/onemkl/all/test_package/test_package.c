// https://www.intel.com/content/www/us/en/docs/onemkl/code-samples-lapack/2024-1/cgesv-example-c.html

/*******************************************************************************
*  Copyright (C) 2009-2015 Intel Corporation. All Rights Reserved.
*  The information and material ("Material") provided below is owned by Intel
*  Corporation or its suppliers or licensors, and title to such Material remains
*  with Intel Corporation or its suppliers or licensors. The Material contains
*  proprietary information of Intel or its suppliers and licensors. The Material
*  is protected by worldwide copyright laws and treaty provisions. No part of
*  the Material may be copied, reproduced, published, uploaded, posted,
*  transmitted, or distributed in any way without Intel's prior express written
*  permission. No license under any patent, copyright or other intellectual
*  property rights in the Material is granted to or conferred upon you, either
*  expressly, by implication, inducement, estoppel or otherwise. Any license
*  under such intellectual property rights must be express and approved by Intel
*  in writing.
*
********************************************************************************
*/
/*
   CGESV Example.
   ==============

   The program computes the solution to the system of linear
   equations with a square matrix A and multiple
   right-hand sides B, where A is the coefficient matrix:

   (  1.23, -5.50) (  7.91, -5.38) ( -9.80, -4.86) ( -7.32,  7.57)
   ( -2.14, -1.12) ( -9.92, -0.79) ( -9.18, -1.12) (  1.37,  0.43)
   ( -4.30, -7.10) ( -6.47,  2.52) ( -6.51, -2.67) ( -5.86,  7.38)
   (  1.27,  7.29) (  8.90,  6.92) ( -8.82,  1.25) (  5.41,  5.37)

   and B is the right-hand side matrix:

   (  8.33, -7.32) ( -6.11, -3.81)
   ( -6.18, -4.80) (  0.14, -7.71)
   ( -5.71, -2.80) (  1.41,  3.40)
   ( -1.60,  3.08) (  8.54, -4.05)

   Description.
   ============

   The routine solves for X the system of linear equations A*X = B,
   where A is an n-by-n matrix, the columns of matrix B are individual
   right-hand sides, and the columns of X are the corresponding
   solutions.

   The LU decomposition with partial pivoting and row interchanges is
   used to factor A as A = P*L*U, where P is a permutation matrix, L
   is unit lower triangular, and U is upper triangular. The factored
   form of A is then used to solve the system of equations A*X = B.

   Example Program Results.
   ========================

 CGESV Example Program Results

 Solution
 ( -1.09, -0.18) (  1.28,  1.21)
 (  0.97,  0.52) ( -0.22, -0.97)
 ( -0.20,  0.19) (  0.53,  1.36)
 ( -0.59,  0.92) (  2.22, -1.00)

 Details of LU factorization
 ( -4.30, -7.10) ( -6.47,  2.52) ( -6.51, -2.67) ( -5.86,  7.38)
 (  0.49,  0.47) ( 12.26, -3.57) ( -7.87, -0.49) ( -0.98,  6.71)
 (  0.25, -0.15) ( -0.60, -0.37) (-11.70, -4.64) ( -1.35,  1.38)
 ( -0.83, -0.32) (  0.05,  0.58) (  0.93, -0.50) (  2.66,  7.86)

 Pivot indices
      3      3      3      4
*/
#include <stdlib.h>
#include <stdio.h>
#include <mkl_types.h>

/* Complex datatype */
struct _fcomplex { float re, im; };
typedef struct _fcomplex fcomplex;

/* CGESV prototype */
extern void cgesv( MKL_INT* n, MKL_INT* nrhs, fcomplex* a, MKL_INT* lda, MKL_INT* ipiv,
                fcomplex* b, MKL_INT* ldb, MKL_INT* info );
/* Auxiliary routines prototypes */
extern void print_matrix( char* desc, int m, int n, fcomplex* a, int lda );
extern void print_int_vector( char* desc, int n, MKL_INT* a );

/* Parameters */
#define N 4
#define NRHS 2
#define LDA N
#define LDB N

/* Main program */
int main() {
        /* Locals */
        MKL_INT n = N, nrhs = NRHS, lda = LDA, ldb = LDB, info;
        /* Local arrays */
        MKL_INT ipiv[N];
        fcomplex a[LDA*N] = {
           { 1.23f, -5.50f}, {-2.14f, -1.12f}, {-4.30f, -7.10f}, { 1.27f,  7.29f},
           { 7.91f, -5.38f}, {-9.92f, -0.79f}, {-6.47f,  2.52f}, { 8.90f,  6.92f},
           {-9.80f, -4.86f}, {-9.18f, -1.12f}, {-6.51f, -2.67f}, {-8.82f,  1.25f},
           {-7.32f,  7.57f}, { 1.37f,  0.43f}, {-5.86f,  7.38f}, { 5.41f,  5.37f}
        };
        fcomplex b[LDB*NRHS] = {
           { 8.33f, -7.32f}, {-6.18f, -4.80f}, {-5.71f, -2.80f}, {-1.60f,  3.08f},
           {-6.11f, -3.81f}, { 0.14f, -7.71f}, { 1.41f,  3.40f}, { 8.54f, -4.05f}
        };
        /* Executable statements */
        printf( " CGESV Example Program Results\n" );
        /* Solve the equations A*X = B */
        cgesv( &n, &nrhs, a, &lda, ipiv, b, &ldb, &info );
        /* Check for the exact singularity */
        if( info > 0 ) {
                printf( "The diagonal element of the triangular factor of A,\n" );
                printf( "U(%lld,%lld) is zero, so that A is singular;\n",
                        (long long)info, (long long)info );
                printf( "the solution could not be computed.\n" );
                exit( 1 );
        }
        /* Print solution */
        print_matrix( "Solution", n, nrhs, b, ldb );
        /* Print details of LU factorization */
        print_matrix( "Details of LU factorization", n, n, a, lda );
        /* Print pivot indices */
        print_int_vector( "Pivot indices", n, ipiv );
        exit( 0 );
} /* End of CGESV Example */

/* Auxiliary routine: printing a matrix */
void print_matrix( char* desc, int m, int n, fcomplex* a, int lda ) {
        int i, j;
        printf( "\n %s\n", desc );
        for( i = 0; i < m; i++ ) {
                for( j = 0; j < n; j++ )
                        printf( " (%6.2f,%6.2f)", a[i+j*lda].re, a[i+j*lda].im );
                printf( "\n" );
        }
}

/* Auxiliary routine: printing a vector of integers */
void print_int_vector( char* desc, int n, MKL_INT* a ) {
        int j;
        printf( "\n %s\n", desc );
        for( j = 0; j < n; j++ ) printf( " %6lld", (long long)a[j] );
        printf( "\n" );
}
