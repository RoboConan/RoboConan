#include <sundials/sundials_types.h>

int main(void) {
#if SUNDIALS_MPI_ENABLED
    SUNComm comm = MPI_COMM_WORLD;
    (void)comm;
#endif
}
