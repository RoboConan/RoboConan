#include <nvector/nvector_serial.h>
#include <sunmatrix/sunmatrix_dense.h>
#include <sunlinsol/sunlinsol_dense.h>
#include <sundials/sundials_types.h>

int main(void)
{
#if SUNDIALS_MPI_ENABLED
  MPI_Init(NULL, NULL);
  SUNComm comm = MPI_COMM_WORLD;
#else
  SUNComm comm = 0;
#endif
  SUNContext sunctx;
  SUNContext_Create(comm, &sunctx);
  N_Vector y = N_VNew_Serial(1, sunctx);
  NV_DATA_S(y)[0] = 2.0;
  SUNMatrix A = SUNDenseMatrix(1, 1, sunctx);
  SUNLinearSolver LS = SUNLinSol_Dense(y, A, sunctx);

  N_Vector v = N_VNew_Serial(1, sunctx);
  N_VScale(2.0, y, v);
  N_VDestroy(v);
  SUNLinSolFree(LS);
  SUNMatDestroy(A);
  N_VDestroy(y);
  SUNContext_Free(&sunctx);
#if SUNDIALS_MPI_ENABLED
  MPI_Finalize();
#endif
  return 0;
}
