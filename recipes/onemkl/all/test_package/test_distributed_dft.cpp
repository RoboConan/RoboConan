#include <mpi.h>
#include <oneapi/mkl/experimental/distributed_dft.hpp>

int main() {
    using namespace oneapi::mkl;
    MPI_Init(nullptr, nullptr);
    experimental::dft::distributed_descriptor<dft::precision::SINGLE, dft::domain::COMPLEX>
        descriptor(MPI_COMM_WORLD, {1});
    MPI_Finalize();
}
