#include <osqp/osqp.h>

int main(void) {
#if TEST_OSQP_SOLVE
    OSQPFloat P_x[] = {4.0, 1.0, 2.0};
    OSQPInt P_i[] = {0, 0, 1};
    OSQPInt P_p[] = {0, 1, 3};
    OSQPFloat q[] = {1.0, 1.0};
    OSQPFloat A_x[] = {1.0, 1.0, 1.0, 1.0};
    OSQPInt A_i[] = {0, 1, 0, 2};
    OSQPInt A_p[] = {0, 2, 4};
    OSQPFloat l[] = {1.0, 0.0, 0.0};
    OSQPFloat u[] = {1.0, 0.7, 0.7};
    OSQPCscMatrix* P = OSQPCscMatrix_new(2, 2, 3, P_x, P_i, P_p);
    OSQPCscMatrix* A = OSQPCscMatrix_new(3, 2, 4, A_x, A_i, A_p);
    OSQPSettings* settings = OSQPSettings_new();
    OSQPSolver* solver = 0;
    OSQPInt result = osqp_setup(&solver, P, q, A, l, u, 3, 2, settings);
    if (!result)
        result = osqp_solve(solver);
    osqp_cleanup(solver);
    OSQPSettings_free(settings);
    OSQPCscMatrix_free(A);
    OSQPCscMatrix_free(P);
    return result;
#else
    OSQPSettings* settings = OSQPSettings_new();
    OSQPSettings_free(settings);
#endif
}
