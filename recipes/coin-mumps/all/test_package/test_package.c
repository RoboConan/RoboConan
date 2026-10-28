#include <math.h>
#include <mumps_mpi.h>
#include <dmumps_c.h>

int main(int argc, char **argv)
{
    DMUMPS_STRUC_C id;
    MUMPS_INT irn[] = {1, 2};
    MUMPS_INT jcn[] = {1, 2};
    double a[] = {1.0, 2.0};
    double rhs[] = {1.0, 4.0};

    MPI_Init(&argc, &argv);
    id.comm_fortran = -987654;
    id.par = 1;
    id.sym = 0;
    id.job = -1;
    dmumps_c(&id);

    id.n = 2;
    id.nnz = 2;
    id.irn = irn;
    id.jcn = jcn;
    id.a = a;
    id.rhs = rhs;
    id.icntl[0] = -1;
    id.icntl[1] = -1;
    id.icntl[2] = -1;
    id.icntl[3] = 0;
    id.job = 6;
    dmumps_c(&id);

    const int failed = id.infog[0] < 0 || fabs(rhs[0] - 1.0) > 1e-12 || fabs(rhs[1] - 2.0) > 1e-12;
    id.job = -2;
    dmumps_c(&id);
    MPI_Finalize();
    return failed;
}
