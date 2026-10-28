#include <iostream>
#include <Eigen/Cholesky>
#include <Eigen/Core>
#include <unsupported/Eigen/MatrixFunctions>
#ifdef EIGEN_USE_SYCL
#include <unsupported/Eigen/CXX11/Tensor>

static void instantiate_sycl_tensor_expression(Eigen::SyclDevice& device,
                                               float* input_data,
                                               float* output_data)
{
    Eigen::TensorMap<Eigen::Tensor<float, 1>> input(input_data, 4);
    Eigen::TensorMap<Eigen::Tensor<float, 1>> output(output_data, 4);
    output.device(device) = input * input;
}

static void instantiate_sycl_kernel(cl::sycl::queue& queue)
{
    queue.single_task([=]() {
        Eigen::Matrix2f matrix;
        matrix.setIdentity();
    });
}
#endif

int main(void)
{
    int const N = 5;
    Eigen::MatrixXi A(N, N);
    A.setRandom();

    std::cout << "A =\n" << A << "\n\n"
              << "A(2..3,:) =\n" << A.middleRows(2, 2) << "\n";

    std::cout << "\n";
#ifdef EIGEN_HAS_OPENMP
    std::cout << "Eigen is using OpenMP with " << Eigen::nbThreads() << " threads.\n";
#else
    std::cout << "Eigen is not using OpenMP.\n";
#endif

#ifdef EIGEN_USE_LAPACKE
    Eigen::MatrixXd positive_definite(2, 2);
    positive_definite << 4.0, 1.0, 1.0, 3.0;
    if (positive_definite.llt().info() != Eigen::Success)
        return 1;
#endif

}
